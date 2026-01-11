from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from math import sqrt

from app.domain.models import DailyRecord


@dataclass(frozen=True)
class BaselineStats:
    mean: Optional[float]
    std: Optional[float]
    n: int  # number of non-null observations used


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs)


def _std(xs: List[float], mu: float) -> float:
    # Population std 
    if len(xs) == 0:
        return 0.0
    var = sum((x - mu) ** 2 for x in xs) / len(xs)
    return sqrt(var)


def _get_metric_value(r: DailyRecord, key: str) -> Optional[float]:
    # Map is explicit to avoid magic getattr mistakes
    if key == "recovery_value":
        return r.recovery_value
    if key == "sleep_duration":
        return r.sleep_duration
    if key == "sleep_consistency":
        return r.sleep_consistency
    if key == "exercise_load":
        return r.exercise_load
    if key == "nutrition_value":
        return r.nutrition_value
    raise ValueError(f"Unknown metric key: {key}")


def compute_individual_baselines(
    records: List[DailyRecord],
    metric_key: str,
    window_days: int,
) -> BaselineStats:
    """
    Compute baseline stats (mean/std) for a metric over the last `window_days`
    worth of records in the provided list.

    Assumptions:
    - `records` contains one item per day (or close enough).
    - `records` may contain None values for missing metrics; these are ignored.
    - We treat the *last* `window_days` entries as the window.
    """
    if window_days <= 0:
        raise ValueError("window_days must be > 0")

    window = records[-window_days:] if len(records) >= window_days else records
    xs: List[float] = []
    for r in window:
        v = _get_metric_value(r, metric_key)
        if v is None:
            continue
        xs.append(float(v))

    if len(xs) == 0:
        return BaselineStats(mean=None, std=None, n=0)

    mu = _mean(xs)
    sd = _std(xs, mu)
    return BaselineStats(mean=mu, std=sd, n=len(xs))


def compute_cumulative_baselines(
    records: List[DailyRecord],
    window_days: int,
    metric_keys: Optional[List[str]] = None,
    ) -> Dict[str, BaselineStats]:
    """
    Compute baseline stats for multiple metrics over the same window.
    Returns a dict keyed by metric name -> BaselineStats.
    """
    if metric_keys is None:
        metric_keys = [
            "recovery_value",
            "sleep_duration",
            "sleep_consistency",
            "exercise_load",
            "nutrition_value",
        ]

    baselines: Dict[str, BaselineStats] = {}
    for key in metric_keys:
        baselines[key] = compute_individual_baselines(records, key, window_days)
    return baselines


def z_score(value: float, baseline: BaselineStats) -> Optional[float]:
    """
    Compute z-score relative to baseline. Returns None if baseline missing.
    If std is 0 (no variation), returns 0.0 when value equals mean, else None.
    """
    if baseline.mean is None or baseline.std is None or baseline.n == 0:
        return None
    if baseline.std == 0:
        # If no variance, z-score isn't meaningful unless it's exactly the mean.
        return 0.0 if value == baseline.mean else None
    return (value - baseline.mean) / baseline.std
