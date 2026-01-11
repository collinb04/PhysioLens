# app/services/analytics/pipeline.py
"""
End-to-end pipeline orchestrator.

This file glues together:
- loading data
- computing baselines
- detecting dips
- stability evaluation
- pareto attribution
- insight creation
- evidence timeseries

Routes should call THIS, not re-implement logic.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Optional

from app.domain.constants import AnalysisAssumptions
from app.domain.models import DailyRecord
from app.services.analytics.baselines import compute_individual_baselines, compute_cumulative_baselines
from app.services.analytics.dips import detect_recovery_dips, DipThresholds, DipDetectionResult
from app.services.analytics.pareto_calculation import compute_pareto_attribution, AttributionThresholds, ParetoResult
from app.services.analytics.stability import is_stable_recovery, StabilityResult
from app.services.analytics.insights import build_insight, extract_latest_values, Insight
from app.services.analytics.evidence import build_timeseries

# You should implement this in app/services/ingest/store.py
# For now, pipeline expects you have:
#   load_user_records(user_id: str) -> List[DailyRecord]
from app.services.ingest.store import load_user_records  # adjust if needed


def run_pipeline(
    user_id: str,
    assumptions: AnalysisAssumptions = AnalysisAssumptions(),
    window_days: Optional[int] = None,
    dip_thresholds: DipThresholds = DipThresholds(),
    abnormal_thresholds: AttributionThresholds = AttributionThresholds(),
) -> Dict:
    """
    Returns a dict with:
      - summary: Pareto + insight + meta
      - timeseries: daily evidence series
      - debug: optional internal details (safe to omit in production)

    window_days defaults to assumptions.min_history_days if not provided.
    """
    if window_days is None:
        window_days = assumptions.min_history_days

    # 1) Load + sort records
    records: List[DailyRecord] = load_user_records(user_id)
    records = sorted(records, key=lambda r: r.date)

    # 2) Window the data for analysis (last N days)
    if len(records) > window_days:
        records_w = records[-window_days:]
    else:
        records_w = records

    # 3) Compute baselines (inputs + recovery) using ONE consistent method
    baselines = compute_cumulative_baselines(
        records=records_w,
        window_days=assumptions.baseline_window_days,  # or assumptions.correlation_window_days if that's your field
    )

    recovery_baseline = baselines["recovery_value"]


    # 4) Detect dips (recovery-only)
    dips_all = detect_recovery_dips(
        records=records_w,
        recovery_baseline=recovery_baseline,
        assumptions=assumptions,
        thresholds=dip_thresholds,
    )

    # If your detect_recovery_dips currently returns List[DipEvent],
    # you should adapt it to DipDetectionResult (recommended).
    # If you already updated dips.py to return DipDetectionResult, this will be unnecessary.
    if isinstance(dips_all, list):
        # Back-compat adapter: split by kind (large vs persistent) and dedupe into all
        large = [d for d in dips_all if d.kind == "large"]
        persistent = [d for d in dips_all if d.kind == "persistent"]
        # Dedup large-preferred for "all"
        by_date = {}
        for d in persistent:
            by_date[d.date] = d
        for d in large:
            by_date[d.date] = d
        dips_result = DipDetectionResult(large=large, persistent=persistent, all=[by_date[k] for k in sorted(by_date)])
    else:
        dips_result = dips_all  # type: ignore

    # 5) Stability evaluation (based on recovery baseline + dip count)
    stability: StabilityResult = is_stable_recovery(
        records=records_w,
        recovery_baseline=recovery_baseline,
        dip_count=len(dips_result.all),
        assumptions=assumptions,
    )

    # 6) Pareto attribution (only meaningful if not stable; still safe to run either way)
    pareto: ParetoResult = compute_pareto_attribution(
        records=records_w,
        dips_result=dips_result,
        baselines=baselines,
        assumptions=assumptions,
        thresholds=abnormal_thresholds,
    )

    # 7) Insight generation (actionable = leverage + current state + stability)
    latest_values = extract_latest_values(records_w)
    insight: Insight = build_insight(
        pareto=pareto,
        dips_result=dips_result,
        recovery_stable=stability.stable,
        baselines=baselines,
        latest_values=latest_values,
        assumptions=assumptions,
        resources_by_factor=None,  # add later if you implement curated resources
    )

    # 8) Evidence timeseries for UI
    timeseries = build_timeseries(
        records=records_w,
        dips_result=dips_result,
        baselines=baselines,
        pareto=pareto,
        thresholds=abnormal_thresholds,
    )

    summary = {
        "user_id": user_id,
        "window_days": window_days,
        "stable": stability.stable,
        "factors": [
            {"key": d.key, "percent": d.percent, "occurrences": d.occurrences, "avg_abs_z": d.avg_abs_z}
            for d in pareto.factors_ranked
        ],
        "dominant_key": pareto.dominant_key,
        "insight": asdict(insight),
        "meta": {
            "stability": stability.meta,
            "pareto": pareto.meta,
            "dip_count": len(dips_result.all),
            "large_dip_count": len(dips_result.large),
            "persistent_dip_count": len(dips_result.persistent),
        },
    }

    debug = {
        "latest_values": latest_values,
        "baselines": {
            k: {"mean": v.mean, "std": v.std, "n": v.n} for k, v in baselines.items()
        },
        "dips": [
            {
                "date": d.date.isoformat(),
                "kind": d.kind,
                "recovery_value": d.recovery_value,
                "baseline_mean": d.baseline_mean,
                "z": d.z,
                "magnitude": d.magnitude,
            }
            for d in dips_result.all
        ],
    }

    return {"summary": summary, "timeseries": timeseries, "debug": debug}
