"""
Explicit analysis constants used by the recovery-behavior
relationship evaluation pipeline.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisAssumptions:
    """
    Configuration object defining default analytical constants.

    These are conservative starting points chosen to prioritize
    stability, interpretability, and explainability over sensitivity.
    """

    # Temporal constants
    min_history_days: int = 30 # Minimum amount of days to complete analysis
    baseline_days_window: int = 14 # Rolling window for stability evaluation
    max_lag_days: int = 3 # Maximum temporal offset considered for a lag effect

    # Signal stability constants, min. strength of relationships for trust
    min_observations: int = 10
    min_consistent_windows: int = 3

    # Thresholds (heuristic in comparison to causal)
    min_effect_size: float = 0.15
    max_noise_ratio: float = 0.4

    # Output constraints
    max_explanatory_factors: int = 3
