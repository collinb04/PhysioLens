import pytest
from dataclasses import dataclass
from typing import Optional, List

from app.services.analytics.baselines import (
    BaselineStats,
    compute_individual_baselines,
    compute_cumulative_baselines,
    z_score,
)

@dataclass
class DummyRecord:
    recovery_value: Optional[float] = None
    sleep_duration: Optional[float] = None
    sleep_consistency: Optional[float] = None
    excercise_data_point: Optional[float] = None
    nutrition_data_point: Optional[float] = None


def test_compute_individual_baselines_uses_last_window_and_ignores_none():
    """
    Verifies:
    - Only last `days_window` records are used
    - None values are ignored
    - mean/std are population stats
    """
    records: List[DummyRecord] = [
        DummyRecord(sleep_duration=100),   # outside window
        DummyRecord(sleep_duration=None),  # outside window
        DummyRecord(sleep_duration=2),     # in window
        DummyRecord(sleep_duration=None),  # in window (ignored)
        DummyRecord(sleep_duration=4),     # in window
    ]

    stats = compute_individual_baselines(records, "sleep_duration", days_window=3)

    # Window is last 3: [2, None, 4] -> xs = [2,4]
    assert stats.n == 2
    assert stats.mean == pytest.approx(3.0, abs=1e-9)
    # population std for [2,4] around mean 3 is 1.0
    assert stats.std == pytest.approx(1.0, abs=1e-9)


def test_compute_individual_baselines_all_missing_returns_none_baseline():
    records = [DummyRecord(sleep_duration=None), DummyRecord(sleep_duration=None)]
    stats = compute_individual_baselines(records, "sleep_duration", days_window=7)

    assert stats.n == 0
    assert stats.mean is None
    assert stats.std is None


def test_z_score_handles_std_zero_safely():
    baseline = BaselineStats(mean=5.0, std=0.0, n=10)

    assert z_score(5.0, baseline) == 0.0
    assert z_score(5.0000001, baseline) is None  # strict equality in impl


def test_unknown_metric_key_raises_value_error():
    records = [DummyRecord(recovery_value=50)]
    with pytest.raises(ValueError):
        compute_individual_baselines(records, "not_a_real_metric", days_window=3)


def test_compute_cumulative_baselines_default_keys_present():
    records = [
        DummyRecord(
            recovery_value=50,
            sleep_duration=8,
            sleep_consistency=0.9,
            excercise_data_point=12,
            nutrition_data_point=7,
        ),
        DummyRecord(
            recovery_value=60,
            sleep_duration=None,  # ensure ignored
            sleep_consistency=0.8,
            excercise_data_point=10,
            nutrition_data_point=8,
        ),
    ]

    out = compute_cumulative_baselines(records, days_window=30)

    # default keys must exist
    assert set(out.keys()) == {
        "recovery_value",
        "sleep_duration",
        "sleep_consistency",
        "excercise_data_point",
        "nutrition_data_point",
    }

    assert out["recovery_value"].n == 2
    assert out["sleep_duration"].n == 1  # one None ignored
