from __future__ import annotations
from fastapi import APIRouter, Query
from app.api.schemas import SummaryOut, TimeseriesOut
from app.services.analytics.pipeline import run_pipeline

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/summary", response_model=SummaryOut)
def get_summary(
    user_id: str = Query("user1"),
    days_window: int = Query(30, ge=7, le=365),
):
    result = run_pipeline(user_id=user_id, days_window=days_window)
    return result["summary"]


@router.get("/timeseries", response_model=TimeseriesOut)
def get_timeseries(
    user_id: str = Query("user1"),
    days_window: int = Query(30, ge=7, le=365),
):
    result = run_pipeline(user_id=user_id, days_window=days_window)
    return {
        "user_id": user_id,
        "days_window": days_window,
        "days": result["timeseries"],
    }
