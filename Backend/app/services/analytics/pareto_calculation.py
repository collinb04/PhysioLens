"""
Pareto attribution engine.

Given:
- DailyRecords (recovery + inputs)
- Detected recovery dips (events) from dips.py
- Baselines for inputs (and recovery if needed)

We compute which behavior categories (sleep / exercise / nutrition) most consistently
co-occur with recovery dip events within a plausible lag window.

Key design constraints:
- Dips are defined ONLY from recovery_value (no circular logic).
- Attribution is associative, not causal.
- We penalize "noisy" factors that deviate often without dips.
- We enforce conservative minimum evidence thresholds.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple, Set
from app.domain.daily_record import DailyRecord
from app.domain.config import AnalysisAssumptions  # adjust import if needed
from app.services.analytics.baselines import BaselineStats, z_score
from app.services.analytics.dips import DipEvent, DipDetectionResult  # if you implemented Option A


@dataclass(frozen=True)
class FactorAttribution:
    key: str  # "sleep" | "exercise" | "nutrition"
    percent: float
    raw_score: float
    occurrences: int  # number of dip-events where factor contributed
    avg_abs_z: float  # rough strength summary 


@dataclass(frozen=True)
class ParetoResult:
    factors_ranked: List[FactorAttribution]
    dominant_key: Optional[str]
    meta: Dict[str, object]



# Internal configuration
@dataclass(frozen=True)
class FactorConfig:
    key: str
    # DailyRecord fields that represent this factor
    fields: Tuple[str, ...]


DEFAULT_DRIVERS: Tuple[FactorConfig, ...] = (
    FactorConfig(key="sleep", fields=("sleep_duration", "sleep_consistency")),
    FactorConfig(key="exercise", fields=("excercise_data_point",)),
    FactorConfig(key="nutrition", fields=("nutrition_data_point",)),
)

# Abnormal z-score threshold
@dataclass(frozen=True)
class AttributionThresholds:
    abnormal_abs_z: float = 1.25  


# Helpers
def _index_records_by_date(records: List[DailyRecord]) -> Dict[date, DailyRecord]:
    return {r.date: r for r in records}


def _get_field_value(r: DailyRecord, field: str) -> Optional[float]:
    v = getattr(r, field, None)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def _is_factor_abnormal(
    record: DailyRecord,
    factor: FactorConfig,
    baselines: Dict[str, BaselineStats],
    thresholds: AttributionThresholds,
) -> Tuple[bool, float]:
    """
    Returns:
      (abnormal?, abs_z_strength)

    Directional consistency:
    - exercise: only count as contributing to a dip if it's ABOVE baseline (z > 0)
    - sleep: only count if it's BELOW baseline (z < 0)
    - nutrition: only count if it's BELOW baseline (z < 0)

    Note: This is associative, not causal. It's a conservative filter to avoid crediting
    "good-direction" deviations as explanations for recovery drops.
    """
    # Determine the signed z-score that best represents this factor on this day.
    best_signed_z: Optional[float] = None
    best_abs_z: float = 0.0

    for field in factor.fields:
        b = baselines.get(field)
        if b is None:
            continue
        val = _get_field_value(record, field)
        if val is None:
            continue
        z = z_score(val, b)
        if z is None:
            continue

        az = abs(float(z))
        if az > best_abs_z:
            best_abs_z = az
            best_signed_z = float(z)

    if best_signed_z is None:
        return (False, 0.0)

    # Direction filter (plausibly harmful direction for recovery dips)
    if factor.key == "exercise":
        # High training load is the hypothesized stressor
        if best_signed_z <= 0:
            return (False, 0.0)
    elif factor.key in ("sleep", "nutrition"):
        # Lower sleep / worse consistency or under-nutrition is the hypothesized stressor
        if best_signed_z >= 0:
            return (False, 0.0)

    return (best_abs_z >= thresholds.abnormal_abs_z, float(best_abs_z))



def _dip_weight(dip: DipEvent) -> float:
    if dip.kind == "large":
        return 1.25
    return 1.0 # Persistent dip


def _date_range(start: date, end: date) -> List[date]:
    """Inclusive start, inclusive end."""
    days = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def _count_consistent_windows(
    dip_dates: List[date],
    contributing_dates: Set[date],
    days_window: int,
) -> int:
    """
    Counts how many rolling windows contain at least one dip date where
    this factor contributed (within lag window).

    We anchor windows to dip dates for interpretability.
    """
    if not dip_dates:
        return 0

    # Sort dip dates and create non-overlapping windows of size days_window
    dip_dates = sorted(dip_dates)
    windows = 0
    i = 0
    while i < len(dip_dates):
        w_start = dip_dates[i]
        w_end = w_start + timedelta(days=days_window - 1)
        # did the factor contribute to ANY dip in this window?
        hit = any((d in contributing_dates) for d in dip_dates[i:] if d <= w_end)
        if hit:
            windows += 1
        # advance i to first dip date after this window
        while i < len(dip_dates) and dip_dates[i] <= w_end:
            i += 1
    return windows


# Main entry point
def compute_pareto_attribution(
    records: List[DailyRecord],
    dips_result: DipDetectionResult,
    baselines: Dict[str, BaselineStats],
    constants: AnalysisAssumptions,
    factors: Tuple[FactorConfig, ...] = DEFAULT_DRIVERS,
    thresholds: AttributionThresholds = AttributionThresholds(),
) -> ParetoResult:
    """
    Returns Pareto attribution across factors:
    - ranked factors with percents
    - dominant_key if strong enough, else None

    Required baselines keys:
      "sleep_duration", "sleep_consistency", "excercise_data_point", "nutrition_data_point"
    """
    # Gate on minimum history (don’t hallucinate signal)
    if len(records) < constants.min_history_days:
        return ParetoResult(
            factors_ranked=[],
            dominant_key=None,
            meta={"reason": "insufficient_history", "history_days": len(records)},
        )

    all_dips: List[DipEvent] = list(dips_result.all)
    if len(all_dips) == 0:
        return ParetoResult(
            factors_ranked=[],
            dominant_key=None,
            meta={"reason": "no_dips", "dip_count": 0},
        )

    rec_by_date = _index_records_by_date(records)

    # Build the set of "dip context dates" (dip day + prior lag days)
    dip_context_dates: Set[date] = set()
    for dip in all_dips:
        for lag in range(0, constants.max_lag_days + 1):
            dip_context_dates.add(dip.date - timedelta(days=lag))

    # Score accumulators
    raw_scores: Dict[str, float] = {d.key: 0.0 for d in factors}
    occurrences: Dict[str, int] = {d.key: 0 for d in factors}
    abs_z_sums: Dict[str, float] = {d.key: 0.0 for d in factors}
    # For window consistency tracking: which dip dates did this factor contribute to?
    contributed_to_dip_dates: Dict[str, Set[date]] = {d.key: set() for d in factors}

    # --- Core attribution loop: iterate dips; check abnormal behavior within lag window ---
    for dip in all_dips:
        dip_w = _dip_weight(dip)

        # For each factor, find if it was abnormal in the dip's lag window
        for factor in factors:
            best_strength = 0.0
            contributed = False

            for lag in range(0, constants.max_lag_days + 1):
                day = dip.date - timedelta(days=lag)
                rec = rec_by_date.get(day)
                if rec is None:
                    continue

                is_abn, strength = _is_factor_abnormal(rec, factor, baselines, thresholds)
                if not is_abn:
                    continue

                contributed = True
                if strength > best_strength:
                    best_strength = strength

            if contributed:
                # Weighted by dip severity kind + strength of deviation
                raw_scores[factor.key] += dip_w * best_strength
                occurrences[factor.key] += 1
                abs_z_sums[factor.key] += best_strength
                contributed_to_dip_dates[factor.key].add(dip.date)

    # If nothing contributed, return "no dominant" cleanly
    if sum(raw_scores.values()) == 0.0:
        return ParetoResult(
            factors_ranked=[],
            dominant_key=None,
            meta={
                "reason": "no_explanatory_signal",
                "dip_count": len(all_dips),
                "max_lag_days": constants.max_lag_days,
            },
        )

    # --- Noise penalty: downweight factors that deviate frequently outside dip context ---
    # Count abnormal days overall and abnormal days inside dip_context_dates
    total_abnormal: Dict[str, int] = {d.key: 0 for d in factors}
    abnormal_in_context: Dict[str, int] = {d.key: 0 for d in factors}

    for r in records:
        for factor in factors:
            is_abn, _strength = _is_factor_abnormal(r, factor, baselines, thresholds)
            if not is_abn:
                continue
            total_abnormal[factor.key] += 1
            if r.date in dip_context_dates:
                abnormal_in_context[factor.key] += 1

    # Apply penalty based on "noise ratio" = abnormal outside context / total abnormal
    for factor in factors:
        tot = total_abnormal[factor.key]
        if tot == 0:
            continue
        noise = tot - abnormal_in_context[factor.key]
        noise_ratio = noise / tot  # 0..1
        # If noise_ratio exceeds max_noise_ratio, reduce score proportionally
        if noise_ratio > constants.max_noise_ratio:
            # penalty factor goes from 1 -> 0 as noise_ratio goes from max_noise_ratio -> 1
            excess = min(1.0, (noise_ratio - constants.max_noise_ratio) / (1.0 - constants.max_noise_ratio))
            penalty = 1.0 - excess
            raw_scores[factor.key] *= penalty

    # Re-check after penalties
    total_score = sum(raw_scores.values())
    if total_score <= 0.0:
        return ParetoResult(
            factors_ranked=[],
            dominant_key=None,
            meta={
                "reason": "all_penalized_as_noise",
                "dip_count": len(all_dips),
                "max_lag_days": constants.max_lag_days,
            },
        )

    # --- Consistency windows: require relationship to recur across time ---
    dip_dates_sorted = sorted([d.date for d in all_dips])
    consistent_ok: Set[str] = set()
    for factor in factors:
        w = _count_consistent_windows(
            dip_dates=dip_dates_sorted,
            contributing_dates=contributed_to_dip_dates[factor.key],
            days_window=constants.baseline_days_window,
        )
        if w >= constants.min_consistent_windows:
            consistent_ok.add(factor.key)
        else:
            # If not consistent, you can either drop it or keep with heavy downweight.
            # Conservative choice: downweight hard.
            raw_scores[factor.key] *= 0.5

    # Normalize to percentages
    total_score = sum(raw_scores.values())
    ranked = sorted(raw_scores.items(), key=lambda kv: kv[1], reverse=True)

    # Build FactorAttribution objects
    factors_ranked: List[FactorAttribution] = []
    for key, score in ranked:
        if score <= 0:
            continue
        pct = (score / total_score) * 100.0
        occ = occurrences.get(key, 0)
        avg_abs_z = (abs_z_sums[key] / occ) if occ > 0 else 0.0

        factors_ranked.append(
            FactorAttribution(
                key=key,
                percent=pct,
                raw_score=score,
                occurrences=occ,
                avg_abs_z=avg_abs_z,
            )
        )

    # Enforce output constraint: top K
    factors_ranked = factors_ranked[: constants.max_explanatory_factors]

    # Determine dominant factor (effect size threshold)
    dominant_key: Optional[str] = None
    if factors_ranked:
        top = factors_ranked[0]
        if (top.percent / 100.0) >= constants.min_effect_size:
            dominant_key = top.key

    meta = {
        "dip_count": len(all_dips),
        "large_dip_count": len(dips_result.large),
        "persistent_dip_count": len(dips_result.persistent),
        "max_lag_days": constants.max_lag_days,
        "baseline_days_window": constants.baseline_days_window,
        "abnormal_abs_z": thresholds.abnormal_abs_z,
        "consistent_factors": sorted(list(consistent_ok)),
    }

    return ParetoResult(factors_ranked=factors_ranked, dominant_key=dominant_key, meta=meta)
