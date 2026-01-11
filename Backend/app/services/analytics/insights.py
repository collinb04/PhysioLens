# app/services/analytics/insights.py
"""
Insight generation.

This module converts analysis outputs (Pareto attribution + baselines + stability)
into concise, actionable (but non-prescriptive) insights.

Design goals:
- Actionable == clarifies what to focus on (leverage) + current state + stability
- Avoid prescriptions, targets, diagnoses, or causal claims
- Template-based language (no LLM / free-form generation)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

from app.domain.models import DailyRecord
from app.domain.constants import AnalysisAssumptions  # adjust import path if needed
from app.services.analytics.baselines import BaselineStats
from app.services.analytics.pareto_calculation import ParetoResult, FactorAttribution, DEFAULT_DRIVERS, AttributionThresholds
from app.services.analytics.dips import DipDetectionResult


@dataclass(frozen=True)
class Insight:
    """
    UI-ready insight payload.
    Keep this small, stable, and easy to render.
    """
    title: str
    body: str
    # Optional structured fields to support UI without parsing text
    primary_factor: Optional[str] = None
    primary_percent: Optional[float] = None
    current_state: Optional[Dict[str, str]] = None  # e.g. {"sleep": "below_normal"}
    stability: Optional[Dict[str, str]] = None      # e.g. {"sleep": "volatile"}
    confidence: str = "low"                         # "low" | "medium" | "high"
    resources: Optional[Dict[str, List[Dict[str, str]]]] = None  # optional


def _band_from_z(z: Optional[float]) -> str:
    """
    Converts a z-score into a simple state label.
    We intentionally avoid absolute targets; this is person-relative.
    """
    if z is None:
        return "unknown"
    if z <= -0.75:
        return "below_normal"
    if z >= 0.75:
        return "above_normal"
    return "within_normal"


def _stability_from_std(b: BaselineStats) -> str:
    """
    Simple stability label for a metric:
    - If std is large relative to mean scale, it is more volatile.
    We keep this conservative and interpretable.
    """
    if b.mean is None or b.std is None or b.n == 0:
        return "unknown"
    # If mean is near 0, std/mean isn't meaningful; fall back to absolute std
    if abs(b.mean) < 1e-9:
        return "volatile" if b.std > 0 else "stable"
    ratio = abs(b.std / b.mean)
    # Conservative cutoffs (tune later if needed)
    if ratio >= 0.15:
        return "volatile"
    return "stable"


def _factor_fields(factor_key: str) -> Tuple[str, ...]:
    """
    Map factor category to its fields for summarizing state/stability.
    Must match pareto.py DEFAULT_DRIVERS categories.
    """
    for d in DEFAULT_DRIVERS:
        if d.key == factor_key:
            return d.fields
    return tuple()


def _factor_state_and_stability(
    factor_key: str,
    baselines: Dict[str, BaselineStats],
    latest_values: Dict[str, Optional[float]],
    # This should match pareto.py abnormal threshold for consistent messaging
    abnormal_thresholds: AttributionThresholds = AttributionThresholds(),
) -> Tuple[str, str]:
    """
    Returns (state, stability) for the factor category.

    - state: below/within/above normal (based on best available field)
    - stability: stable/volatile/unknown (based on baseline std)
    """
    fields = _factor_fields(factor_key)
    if not fields:
        return ("unknown", "unknown")

    # Choose the "strongest" field (largest abs z), similar to pareto factor scoring.
    best_z: Optional[float] = None
    best_field: Optional[str] = None

    for f in fields:
        b = baselines.get(f)
        v = latest_values.get(f)
        if b is None or v is None or b.mean is None or b.std is None or b.n == 0:
            continue
        if b.std == 0:
            z = 0.0 if v == b.mean else None
        else:
            z = (v - b.mean) / b.std

        if z is None:
            continue
        if best_z is None or abs(z) > abs(best_z):
            best_z = float(z)
            best_field = f

    state = _band_from_z(best_z)

    # Stability: we compute per-field and take the "most volatile" for safety
    stabilities: List[str] = []
    for f in fields:
        b = baselines.get(f)
        if b is None:
            continue
        stabilities.append(_stability_from_std(b))

    if not stabilities:
        stability = "unknown"
    elif "volatile" in stabilities:
        stability = "volatile"
    elif "stable" in stabilities:
        stability = "stable"
    else:
        stability = "unknown"

    return (state, stability)


def _confidence_label(
    pareto: ParetoResult,
    dips_result: DipDetectionResult,
    assumptions: AnalysisAssumptions,
) -> str:
    """
    Simple, explainable confidence heuristic.
    Not statistical certainty—just a UI-level trust indicator.
    """
    dip_count = len(dips_result.all)
    large_count = len(dips_result.large)

    if pareto.dominant_key is None:
        return "low"

    # Stronger if more dips, and at least some are large dips
    if dip_count >= max(assumptions.min_observations, 10) and large_count >= 2:
        return "high"

    if dip_count >= 5:
        return "medium"

    return "low"


def build_insight(
    pareto: ParetoResult,
    dips_result: DipDetectionResult,
    recovery_stable: bool,
    baselines: Dict[str, BaselineStats],
    latest_values: Dict[str, Optional[float]],
    assumptions: AnalysisAssumptions,
    resources_by_factor: Optional[Dict[str, List[Dict[str, str]]]] = None,
) -> Insight:
    """
    Main insight constructor.

    Inputs:
    - pareto: result of compute_pareto_attribution()
    - dips_result: dips detection output
    - recovery_stable: stable flag from stability detection
    - baselines: baseline stats for metrics (inputs at least)
    - latest_values: current day's metric values (or most recent available)
    - resources_by_factor: optional curated resources to surface by dominant factor
    """
    # 1) Stable recovery: valid "success" state
    if recovery_stable:
        body = (
            "Recovery has been relatively stable over the selected window. "
            "No dominant recovery factor was detected because there are few meaningful recovery dips to explain."
        )
        return Insight(
            title="Recovery is stable",
            body=body,
            confidence="high",
        )

    # 2) No dips or insufficient signal
    if len(dips_result.all) == 0 or not pareto.factors_ranked:
        reason = pareto.meta.get("reason") if isinstance(pareto.meta, dict) else None
        if reason == "insufficient_history":
            body = "Not enough history to evaluate recovery factors yet. Add more days of data to improve signal."
        elif reason == "no_explanatory_signal":
            body = (
                "Recovery dips were detected, but no behavior factor showed a consistent association within the lag window. "
                "This can happen when inputs are missing or recovery changes are driven by untracked factors."
            )
        else:
            body = (
                "No dominant recovery factor was detected in this window. "
                "This may be due to sparse data, low variability, or multiple small factors contributing at once."
            )

        return Insight(
            title="No dominant recovery factor detected",
            body=body,
            confidence="low",
        )

    # 3) Dominant factor insight (actionable via leverage + state + stability)
    dominant = pareto.dominant_key
    top: FactorAttribution = pareto.factors_ranked[0]

    # Even if dominant_key wasn't set, we can still present the top factor as "most explanatory"
    primary_factor = dominant if dominant is not None else top.key
    primary_percent = float(top.percent)

    state, stability = _factor_state_and_stability(primary_factor, baselines, latest_values)

    # Optional: include runner-up in phrasing (“not Y”) when available
    runner_up = pareto.factors_ranked[1].key if len(pareto.factors_ranked) > 1 else None

    # Title should be instantly scannable
    title = f"Primary recovery-associated factor: {primary_factor.capitalize()}"

    # Body: leverage + current state + stability. No prescriptions.
    parts: List[str] = []
    parts.append(
        f"{primary_factor.capitalize()} explains the largest share of recovery dips in this window ({primary_percent:.0f}%)."
    )
    if runner_up:
        parts.append(f"For you, recovery appears more sensitive to {primary_factor} than to {runner_up}.")

    # State/stability messaging (actionable)
    if state != "unknown":
        state_phrase = {
            "below_normal": "below your normal range",
            "within_normal": "within your normal range",
            "above_normal": "above your normal range",
        }.get(state, "relative to your normal range")
        parts.append(f"Current state: {primary_factor} is {state_phrase}.")
    else:
        parts.append(f"Current state: {primary_factor} is unavailable or missing for recent days.")

    if stability != "unknown":
        stab_phrase = "highly variable" if stability == "volatile" else "consistent"
        parts.append(f"Stability: {primary_factor} has been {stab_phrase} recently.")
    else:
        parts.append(f"Stability: not enough data to evaluate {primary_factor} consistency.")

    body = " ".join(parts)

    confidence = _confidence_label(pareto, dips_result, assumptions)

    insight = Insight(
        title=title,
        body=body,
        primary_factor=primary_factor,
        primary_percent=primary_percent,
        current_state={primary_factor: state},
        stability={primary_factor: stability},
        confidence=confidence,
    )

    # Optional curated resources (education, not advice)
    if resources_by_factor and primary_factor in resources_by_factor:
        insight = Insight(
            **{**insight.__dict__, "resources": {primary_factor: resources_by_factor[primary_factor]}}
        )

    return insight


def extract_latest_values(records: List[DailyRecord]) -> Dict[str, Optional[float]]:
    """
    Convenience helper: extracts the most recent non-null values per metric field.
    Useful because the last day may have missing inputs.

    Returns keys matching DailyRecord field names used by baselines/pareto.
    """
    keys = [
        "sleep_duration",
        "sleep_consistency",
        "exercise_load",
        "nutrition_value",
        "recovery_value",
    ]
    latest: Dict[str, Optional[float]] = {k: None for k in keys}

    for r in reversed(records):
        for k in keys:
            if latest[k] is not None:
                continue
            v = getattr(r, k, None)
            if v is None:
                continue
            try:
                latest[k] = float(v)
            except (TypeError, ValueError):
                continue

        if all(latest[k] is not None for k in keys):
            break

    return latest
