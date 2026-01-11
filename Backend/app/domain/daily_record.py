"""
A standardized core record object of daily attributes.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional, Dict

@dataclass
class DailyRecord:
    date: date

    # Observed outcome
    recovery_value: Optional[float] = None

    # Explanatory Inputs
    sleep_duration: Optional[float] = None
    sleep_consistency: Optional[float] = None 
    excercise_data_point: Optional[int] = None 
    nutrition_data_point: Optional[int] = None 

    # Metadata
    sources: Optional[Dict[str, str]] = None


    