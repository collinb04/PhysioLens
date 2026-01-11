# app/api/schemas.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FactorOut(BaseModel):
    key: str
    percent: float
    occurrences: int
    avg_abs_z: float


class InsightOut(BaseModel):
    title: str
    body: str
    primary_factor: Optional[str] = None
    primary_percent: Optional[float] = None
    current_state: Optional[Dict[str, str]] = None
    stability: Optional[Dict[str, str]] = None
    confidence: str = "low"
    resources: Optional[Dict[str, List[Dict[str, str]]]] = None


class SummaryOut(BaseModel):
    user_id: str
    window_days: int
    stable: bool
    factors: List[FactorOut] = Field(default_factory=list)
    dominant_key: Optional[str] = None
    insight: InsightOut
    meta: Dict[str, Any] = Field(default_factory=dict)


class TimeseriesDayOut(BaseModel):
    date: str
    recovery_value: Optional[float] = None
    sleep_duration: Optional[float] = None
    sleep_consistency: Optional[float] = None
    exercise_load: Optional[float] = None
    nutrition_value: Optional[float] = None

    is_dip: bool
    dip_kind: str

    factor_abnormal: Dict[str, bool]
    factor_abs_z: Dict[str, float]


class TimeseriesOut(BaseModel):
    user_id: str
    window_days: int
    days: List[TimeseriesDayOut]
