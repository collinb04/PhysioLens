"""
Recovery dip detection.

A "dip" is defined by the recovery signal RELATIVE to the user's
personal baseline. We do NOT look at sleep/exercise/nutrition here to avoid
circular logic. Behaviors are only used later during attribution.

dip types:
1) Large dip: a significant single-day drop below baseline.
2) Persistent dip: a smaller drop sustained for multiple consecutive days.

This module returns dip events that downstream attribution can attempt to explain.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from app.domain.models import DailyRecord
from app.domain.constants import AnalysisAssumptions 
from app.services.analytics.baselines import BaselineStats, z_score


@dataclass(frozen=True)
class DipEvent:
    date: date
    recovery_value: float
    baseline_mean: float
    z: float
    magnitude: float  # baseline_mean - recovery_value (positive means worse than baseline)
    kind: str  # "large" | "persistent"

@dataclass(frozen=True)
class DipDetectionResult:
    large: List[DipEvent]
    persistent: List[DipEvent]
    all: List[DipEvent] # no duplications with large preference

@dataclass(frozen=True)
class DipThresholds:
    """
    Heuristic thresholds for dip detection.

    - large_dip_z: single-day dip threshold
    - persistent_dip_z: threshold for days that qualify as part of a persistent run
    - persistent_days: minimum consecutive days for a persistent dip run
    """
    large_dip_z: float = -1.25
    persistent_dip_z: float = -0.75
    persistent_days: int = 2


def detect_recovery_dips(
    records: List[DailyRecord],
    recovery_baseline: BaselineStats,
    assumptions: AnalysisAssumptions,
    thresholds: DipThresholds = DipThresholds(),
) -> List[DipEvent]:
    """
    Detect recovery dips from a list of DailyRecord objects.

    Requirements / gates:
    - Must have at least assumptions.min_history_days records (conservative)
    - Must have recovery_baseline.n >= assumptions.min_observations
    - Dip detection is based ONLY on recovery_value deviations

    Returns:
    - A list of DipEvent, ordered by date, with duplicate dates removed
      (if a day is both "large" and part of a "persistent" run, it is labeled "large").
    """
    if len(records) < assumptions.min_history_days:
        return []

    if recovery_baseline.mean is None or recovery_baseline.std is None:
        return []

    if recovery_baseline.n < assumptions.min_observations:
        return []

    # Compute per-day z-scores (None when not computable)
    per_day: List[tuple[DailyRecord, Optional[float]]] = []
    for r in records:
        if r.recovery_value is None:
            per_day.append((r, None))
            continue
        z = z_score(float(r.recovery_value), recovery_baseline)
        per_day.append((r, z))

    dips: List[DipEvent] = []

    # Single day large dips
    for r, z in per_day:
        if z is None or r.recovery_value is None:
            continue
        if z <= thresholds.large_dip_z:
            mu = float(recovery_baseline.mean)
            rv = float(r.recovery_value)
            dips.append(
                DipEvent(
                    date=r.date,
                    recovery_value=rv,
                    baseline_mean=mu,
                    z=float(z),
                    magnitude=mu - rv,
                    kind="large",
                )
            )

    # 2) Consecutive days below a threshold | persistent dips
    run: List[DipEvent] = []
    for r, z in per_day:
        if z is None or r.recovery_value is None:
            # break a run on missing/unscorable recovery
            if len(run) >= thresholds.persistent_days:
                dips.extend(run)
            run = []
            continue

        if z <= thresholds.persistent_dip_z:
            mu = float(recovery_baseline.mean)
            rv = float(r.recovery_value)
            run.append(
                DipEvent(
                    date=r.date,
                    recovery_value=rv,
                    baseline_mean=mu,
                    z=float(z),
                    magnitude=mu - rv,
                    kind="persistent",
                )
            )
        else:
            # close run if long enough
            if len(run) >= thresholds.persistent_days:
                dips.extend(run)
            run = []

    # close trailing run
    if len(run) >= thresholds.persistent_days:
        dips.extend(run)

    # Deduplicate by date: prefer "large" over "persistent" if both exist
    by_date: dict[date, DipEvent] = {}
    for d in dips:
        existing = by_date.get(d.date)
        if existing is None:
            by_date[d.date] = d
            continue
        if existing.kind == "persistent" and d.kind == "large":
            by_date[d.date] = d

    # Return chronologically
    return [by_date[k] for k in sorted(by_date.keys())]
