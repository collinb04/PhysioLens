"""
Explicit analysis assumptions used by the recovery-behavior
relationship evaluation pipeline.

These values are intentionally centralized to make assumptions
visible, reviewable, and easy to adjust as evidence or requirements change.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisAssumptions:
    """
    Configuration object defining default analytical assumptions.

    These are conservative starting points chosen to prioritize
    stability, interpretability, and explainability over sensitivity.
    """

    # Temporal assumptions
    min_history_days: int = 30 # Minimum amount of days to complete analysis
    baseline_window_days: int = 14 # Rolling window for stability evaluation
    max_lag_days: int = 3 # Maximum temporal offset considered for a lag effect

    # Signal stability assumptions, min. strength of relationships for trust
    min_observations: int = 10
    min_consistent_windows: int = 3

    # Thresholds (heuristic in comparison to causal)
    min_effect_size: float = 0.15
    max_noise_ratio: float = 0.4

    # Output constraints
    max_explanatory_factors: int = 3
