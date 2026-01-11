import pytest
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional, List

from app.services.analytics.baselines import BaselineStats
from app.services.analytics.pareto_calculation import compute_pareto_attribution, AttributionThresholds
from app.services.analytics.dips import DipEvent, DipDetectionResult


@dataclass
class DummyRecord:
    date: date
    recovery_value: Optional[float] = None
    sleep_duration: Optional[float] = None
    sleep_consistency: Optional[float] = None
    excercise_data_point: Optional[float] = None
    nutrition_data_point: Optional[float] = None


@dataclass
class DummyAssumptions:
    min_history_days: int = 1
    max_lag_days: int = 0
    max_noise_ratio: float = 1.0  # set to 1.0 so noise penalty never triggers
    baseline_days_window: int = 7
    min_consistent_windows: int = 1
    max_explanatory_factors: int = 3
    min_effect_size: float = 0.25  # 25%


def _mk_records(
    days: int,
    start: date = date(2026, 1, 1),
    *,
    exercise_vals: Optional[List[Optional[float]]] = None,
    sleep_vals: Optional[List[Optional[float]]] = None,
) -> List[DummyRecord]:
    out: List[DummyRecord] = []
    for i in range(days):
        ex = exercise_vals[i] if exercise_vals is not None else None
        sl = sleep_vals[i] if sleep_vals is not None else None
        out.append(
            DummyRecord(
                date=start + timedelta(days=i),
                recovery_value=50.0,
                excercise_data_point=ex,
                sleep_duration=sl,
            )
        )
    return out


def _mk_dip(date_: date, kind: str = "large") -> DipEvent:
    return DipEvent(
        date=date_,
        recovery_value=50.0,
        baseline_mean=60.0,
        z=-2.0,
        magnitude=10.0,
        kind=kind,
    )

def test_pareto_returns_insufficient_history_gate():
    records = _mk_records(3, start=date(2026, 1, 1))
    dips = DipDetectionResult(large=[], persistent=[], all=[_mk_dip(date(2026, 1, 2))])

    baselines = {
        "excercise_data_point": BaselineStats(mean=0.0, std=1.0, n=10),
        "sleep_duration": BaselineStats(mean=8.0, std=1.0, n=10),
        "sleep_consistency": BaselineStats(mean=0.8, std=0.1, n=10),
        "nutrition_data_point": BaselineStats(mean=10.0, std=1.0, n=10),
    }

    constants = DummyAssumptions(min_history_days=10)
    out = compute_pareto_attribution(records, dips, baselines, constants)

    assert out.dominant_key is None
    assert out.factors_ranked == []
    assert out.meta.get("reason") == "insufficient_history"


def test_pareto_returns_no_dips_gate():
    records = _mk_records(10, start=date(2026, 1, 1))
    dips = DipDetectionResult(large=[], persistent=[], all=[])

    baselines = {
        "excercise_data_point": BaselineStats(mean=0.0, std=1.0, n=10),
        "sleep_duration": BaselineStats(mean=8.0, std=1.0, n=10),
        "sleep_consistency": BaselineStats(mean=0.8, std=0.1, n=10),
        "nutrition_data_point": BaselineStats(mean=10.0, std=1.0, n=10),
    }

    constants = DummyAssumptions(min_history_days=1)
    out = compute_pareto_attribution(records, dips, baselines, constants)

    assert out.dominant_key is None
    assert out.factors_ranked == []
    assert out.meta.get("reason") == "no_dips"
    assert out.meta.get("dip_count") == 0


def test_pareto_exercise_dominant_and_percents_sum_to_100():
    """
    Exercise contributes only if z > 0 (above baseline).
    We'll create a single dip day where exercise is strongly above baseline.
    With max_noise_ratio=1.0 and min_consistent_windows=1, it should pass gates.
    """
    start = date(2026, 1, 1)
    dip_day = start + timedelta(days=4)

    # exercise is mostly normal (0), but very high on dip day (3.0 => z=3)
    records = _mk_records(
        10,
        start=start,
        exercise_vals=[0, 0, 0, 0, 3.0, 0, 0, 0, 0, 0],
        sleep_vals=[8, 8, 8, 8, 8, 8, 8, 8, 8, 8],
    )

    dips = DipDetectionResult(
        large=[_mk_dip(dip_day, kind="large")],
        persistent=[],
        all=[_mk_dip(dip_day, kind="large")],
    )

    baselines = {
        # exercise baseline mean=0 std=1 => z=3.0 on dip day => abnormal (>= 1.25)
        "excercise_data_point": BaselineStats(mean=0.0, std=1.0, n=30),
        # sleep baseline mean=8 std=1 => z=0 => not abnormal
        "sleep_duration": BaselineStats(mean=8.0, std=1.0, n=30),
        "sleep_consistency": BaselineStats(mean=0.8, std=0.1, n=30),
        "nutrition_data_point": BaselineStats(mean=10.0, std=1.0, n=30),
    }

    constants = DummyAssumptions(
        min_history_days=1,
        max_lag_days=0,
        max_noise_ratio=1.0,
        baseline_days_window=7,
        min_consistent_windows=1,
        max_explanatory_factors=3,
        min_effect_size=0.20,
    )

    out = compute_pareto_attribution(
        records,
        dips,
        baselines,
        constants,
        thresholds=AttributionThresholds(abnormal_abs_z=1.25),
    )

    assert out.dominant_key == "exercise"
    assert len(out.factors_ranked) >= 1
    assert out.factors_ranked[0].key == "exercise"

    # Non-brittle percent checks
    pct_sum = sum(f.percent for f in out.factors_ranked)
    assert pct_sum == pytest.approx(100.0, abs=1e-6)
    assert out.factors_ranked[0].percent >= 20.0  # satisfies min_effect_size in this setup


def test_pareto_direction_filter_blocks_sleep_if_sleep_is_high_not_low():
    """
    Sleep only contributes if z < 0 (below baseline).
    We'll make sleep VERY HIGH on the dip day (z positive), which is abnormal by magnitude
    but should be excluded by the directional filter => no_explanatory_signal.
    """
    start = date(2026, 1, 1)
    dip_day = start + timedelta(days=2)

    records = _mk_records(
        7,
        start=start,
        exercise_vals=[None] * 7,
        sleep_vals=[8.0, 8.0, 12.0, 8.0, 8.0, 8.0, 8.0],  
    )

    dips = DipDetectionResult(
        large=[_mk_dip(dip_day, kind="large")],
        persistent=[],
        all=[_mk_dip(dip_day, kind="large")],
    )

    baselines = {
        "excercise_data_point": BaselineStats(mean=0.0, std=1.0, n=30),
        "sleep_duration": BaselineStats(mean=8.0, std=1.0, n=30),  
        "sleep_consistency": BaselineStats(mean=0.8, std=0.1, n=30),
        "nutrition_data_point": BaselineStats(mean=10.0, std=1.0, n=30),
    }

    constants = DummyAssumptions(min_history_days=1, max_lag_days=0, max_noise_ratio=1.0)
    out = compute_pareto_attribution(
        records,
        dips,
        baselines,
        constants,
        thresholds=AttributionThresholds(abnormal_abs_z=1.25),
    )

    assert out.dominant_key is None
    assert out.factors_ranked == []
    assert out.meta.get("reason") == "no_explanatory_signal"
