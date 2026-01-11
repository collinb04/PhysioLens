"""
This module decides whether recovery has been "stable" over the analysis window.
Stable means: low variability and few/no meaningful dip events.

This is a valid outcome (not an error). If stable=True, the system should avoid
ranking factors as "dominant" because there's little recovery breakdown to explain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from app.domain.daily_record import DailyRecord
from app.domain.config import AnalysisAssumptions  
from app.services.analytics.baselines import BaselineStats


@dataclass(frozen=True)
class StabilityResult:
    stable: bool
    meta: Dict[str, object]


def _collect_recovery_values(records: List[DailyRecord]) -> List[float]:
    xs: List[float] = []
    for r in records:
        if r.recovery_value is None:
            continue
        try:
            xs.append(float(r.recovery_value))
        except (TypeError, ValueError):
            continue
    return xs


def is_stable_recovery(
    records: List[DailyRecord],
    recovery_baseline: BaselineStats,
    dip_count: int,
    constants: AnalysisAssumptions,
) -> StabilityResult:
    """
    Returns:
    - StabilityResult(stable=bool, meta=dict)
    """
    # Gate: enough history
    if len(records) < constants.min_history_days:
        return StabilityResult(
            stable=False,
            meta={"reason": "insufficient_history", "history_days": len(records)},
        )

    if recovery_baseline.mean is None or recovery_baseline.std is None or recovery_baseline.n == 0:
        return StabilityResult(
            stable=False,
            meta={"reason": "missing_recovery_baseline"},
        )

    if recovery_baseline.n < constants.min_observations:
        return StabilityResult(
            stable=False,
            meta={"reason": "insufficient_recovery_observations", "n": recovery_baseline.n},
        )

    mu = float(recovery_baseline.mean)
    sd = float(recovery_baseline.std)

    # Coefficient of variation (std/mean) as a scale-free stability measure
    # If mean is ~0, fall back to raw std comparison.
    if abs(mu) < 1e-9:
        cv = None
    else:
        cv = abs(sd / mu)

    # Intentionally conservative- tune later if needed.
    cv_threshold = 0.08
    allowed_dips = 0  # definition for stable

    stable_by_variance = (cv is not None and cv <= cv_threshold) or (cv is None and sd == 0.0)
    stable_by_dips = dip_count <= allowed_dips

    stable = stable_by_variance and stable_by_dips

    return StabilityResult(
        stable=stable,
        meta={
            "recovery_mean": mu,
            "recovery_std": sd,
            "recovery_cv": cv,
            "cv_threshold": cv_threshold,
            "dip_count": dip_count,
            "allowed_dips": allowed_dips,
            "stable_by_variance": stable_by_variance,
            "stable_by_dips": stable_by_dips,
        },
    )
