# app/services/analytics/evidence.py
"""
Evidence preparation for UI.

Builds a UI-ready daily timeseries that:
- shows raw values (recovery + inputs)
- marks dip days (large / persistent)
- marks abnormal factor flags (sleep/exercise/nutrition) using the SAME abnormal rule as pareto

This makes the dashboard trustworthy: users can see the same signals the model used.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from app.domain.models import DailyRecord
from app.services.analytics.baselines import BaselineStats, z_score
from app.services.analytics.dips import DipDetectionResult
from app.services.analytics.pareto_calculation import DEFAULT_DRIVERS, AttributionThresholds, FactorConfig, ParetoResult


@dataclass(frozen=True)
class TimeseriesDay:
    date: date
    recovery_value: Optional[float]
    sleep_duration: Optional[float]
    sleep_consistency: Optional[float]
    exercise_load: Optional[float]
    nutrition_value: Optional[float]

    is_dip: bool
    dip_kind: str  # "none" | "large" | "persistent"

    # Factor-level flags for explainability
    factor_abnormal: Dict[str, bool]  # {"sleep": bool, "exercise": bool, "nutrition": bool}
    factor_abs_z: Dict[str, float]    # {"sleep": 0.0.., "exercise": .., "nutrition": ..}


def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _factor_abs_z_for_day(
    record: DailyRecord,
    factor: FactorConfig,
    baselines: Dict[str, BaselineStats],
) -> Optional[float]:
    """
    Returns the factor's per-day strength as the maximum abs z-score among its fields.
    Mirrors pareto logic.
    """
    best: Optional[float] = None
    for field in factor.fields:
        b = baselines.get(field)
        if b is None:
            continue
        val = _safe_float(getattr(record, field, None))
        if val is None:
            continue
        z = z_score(val, b)
        if z is None:
            continue
        az = abs(float(z))
        if best is None or az > best:
            best = az
    return best


def build_timeseries(
    records: List[DailyRecord],
    dips_result: DipDetectionResult,
    baselines: Dict[str, BaselineStats],
    pareto: Optional[ParetoResult] = None,
    thresholds: AttributionThresholds = AttributionThresholds(),
) -> List[Dict]:
    """
    Returns a list of dicts (JSON-ready) for easy API return.

    Note: `pareto` is optional; the timeseries stands on its own.
    """
    dip_kind_by_date: Dict[date, str] = {}
    for d in dips_result.persistent:
        dip_kind_by_date[d.date] = "persistent"
    for d in dips_result.large:
        dip_kind_by_date[d.date] = "large"  # overwrite persistent if both (large preferred)

    out: List[Dict] = []
    for r in records:
        kind = dip_kind_by_date.get(r.date, "none")
        is_dip = kind != "none"

        factor_abn: Dict[str, bool] = {}
        factor_abs_z: Dict[str, float] = {}

        for factor in DEFAULT_DRIVERS:
            abs_z = _factor_abs_z_for_day(r, factor, baselines)
            if abs_z is None:
                factor_abn[factor.key] = False
                factor_abs_z[factor.key] = 0.0
            else:
                factor_abn[factor.key] = abs_z >= thresholds.abnormal_abs_z
                factor_abs_z[factor.key] = float(abs_z)

        out.append(
            {
                "date": r.date.isoformat(),
                "recovery_value": _safe_float(r.recovery_value),
                "sleep_duration": _safe_float(r.sleep_duration),
                "sleep_consistency": _safe_float(r.sleep_consistency),
                "exercise_load": _safe_float(r.exercise_load),
                "nutrition_value": _safe_float(r.nutrition_value),
                "is_dip": is_dip,
                "dip_kind": kind,
                "factor_abnormal": factor_abn,
                "factor_abs_z": factor_abs_z,
            }
        )

    return out
