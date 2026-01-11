import pytest
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional, List

from app.services.analytics.dips import detect_recovery_dips, DipThresholds
from app.services.analytics.baselines import BaselineStats


@dataclass
class DummyAssumptions:
    # Matches the attributes dips.py reads from AnalysisAssumptions
    min_history_days: int = 1
    min_observations: int = 1


@dataclass
class DummyRecord:
    date: date
    recovery_value: Optional[float] = None


def _mk_records(values: List[Optional[float]], start: date = date(2026, 1, 1)) -> List[DummyRecord]:
    return [
        DummyRecord(date=start + timedelta(days=i), recovery_value=v)
        for i, v in enumerate(values)
    ]


def test_detect_recovery_dips_returns_empty_if_not_enough_history_days():
    records = _mk_records([90, 90, 90], start=date(2026, 1, 1))
    baseline = BaselineStats(mean=100.0, std=10.0, n=10)

    constants = DummyAssumptions(min_history_days=10, min_observations=1)
    out = detect_recovery_dips(records, baseline, constants)

    assert out == []


def test_detect_recovery_dips_returns_empty_if_baseline_insufficient_observations():
    records = _mk_records([90, 90, 90, 90], start=date(2026, 1, 1))
    baseline = BaselineStats(mean=100.0, std=10.0, n=1)

    constants = DummyAssumptions(min_history_days=1, min_observations=5)
    out = detect_recovery_dips(records, baseline, constants)

    assert out == []


def test_detect_recovery_dips_persistent_run_and_large_preference_dedup():
    """
    Baseline mean=100 std=10 => z = (rv-100)/10
    - 92 => z=-0.8 qualifies persistent (<= -0.75), not large (<= -1.25)
    - 87 => z=-1.3 qualifies both persistent and large
    Persistent run length is 3, so all 3 days are persistent candidates,
    but the 87 day must be labeled "large" due to dedup preference.
    """
    records = _mk_records([92.0, 87.0, 92.0], start=date(2026, 1, 1))
    baseline = BaselineStats(mean=100.0, std=10.0, n=10)
    constants = DummyAssumptions(min_history_days=1, min_observations=1)

    out = detect_recovery_dips(records, baseline, constants, thresholds=DipThresholds())

    assert [e.date for e in out] == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]
    assert out[0].kind == "persistent"
    assert out[1].kind == "large"       # preference applied
    assert out[2].kind == "persistent"

    # spot-check magnitude sign (baseline_mean - recovery_value)
    assert out[1].magnitude == pytest.approx(100.0 - 87.0, abs=1e-9)


def test_detect_recovery_dips_missing_recovery_breaks_persistent_run():
    """
    Run should break on None recovery_value (z None).
    Sequence:
      day1 92 (would qualify, but run length=1 -> not emitted)
      day2 None -> breaks run
      day3 92 + day4 92 -> run length=2 -> both emitted as persistent
    """
    records = _mk_records([92.0, None, 92.0, 92.0], start=date(2026, 1, 1))
    baseline = BaselineStats(mean=100.0, std=10.0, n=10)
    constants = DummyAssumptions(min_history_days=1, min_observations=1)

    out = detect_recovery_dips(records, baseline, constants, thresholds=DipThresholds(persistent_days=2))

    assert [e.date for e in out] == [date(2026, 1, 3), date(2026, 1, 4)]
    assert all(e.kind == "persistent" for e in out)
