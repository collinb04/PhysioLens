# app/services/ingest/store.py
"""
Hackathon store.

- Loads user data from JSON seed files in /data
- Optionally allows in-memory overrides (useful for POST /ingest demos)

This is intentionally minimal and replaceable with a real DB later.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from app.domain.models import DailyRecord

# In-memory override store (optional, for ingest demos)
_IN_MEMORY: Dict[str, List[DailyRecord]] = {}


def _project_root() -> Path:
    """
    Finds project root assuming this file lives at:
    backend/app/services/ingest/store.py
    """
    return Path(__file__).resolve().parents[3]


def _data_dir() -> Path:
    return _project_root() / "data"


def _parse_date(d: str) -> date:
    # expects YYYY-MM-DD
    return date.fromisoformat(d)


def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _record_from_dict(obj: dict) -> DailyRecord:
    """
    Convert a JSON dict into a DailyRecord.
    JSON keys should match DailyRecord field names.
    """
    return DailyRecord(
        date=_parse_date(obj["date"]),
        recovery_value=_safe_float(obj.get("recovery_value")),
        sleep_duration=_safe_float(obj.get("sleep_duration")),
        sleep_consistency=_safe_float(obj.get("sleep_consistency")),
        exercise_load=_safe_float(obj.get("exercise_load")),
        nutrition_value=_safe_float(obj.get("nutrition_value")),
        sources=obj.get("sources"),
    )


def load_user_records(user_id: str) -> List[DailyRecord]:
    """
    Load records for a user.

    Priority:
    1) In-memory override (if POST /ingest was called)
    2) Seed file: data/seed_<user_id>.json
    3) Fallback: data/seed_user1.json
    """
    if user_id in _IN_MEMORY:
        return sorted(_IN_MEMORY[user_id], key=lambda r: r.date)

    data_dir = _data_dir()
    candidate = data_dir / f"seed_{user_id}.json"
    fallback = data_dir / "seed_user1.json"

    path = candidate if candidate.exists() else fallback
    if not path.exists():
        raise FileNotFoundError(
            f"No seed data found. Expected {candidate} or {fallback}."
        )

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        raise ValueError(f"Seed file must contain a JSON list of daily records: {path}")

    records = [_record_from_dict(item) for item in raw]
    return sorted(records, key=lambda r: r.date)


def save_user_records(user_id: str, records: List[DailyRecord]) -> None:
    """
    Save into in-memory store for the current process.
    (Great for hackathon demos; no DB required.)
    """
    _IN_MEMORY[user_id] = sorted(records, key=lambda r: r.date)


def clear_user_records(user_id: str) -> None:
    """Remove in-memory override for user."""
    _IN_MEMORY.pop(user_id, None)


def export_user_records_to_seed(user_id: str, filename: Optional[str] = None) -> Path:
    """
    Optional helper: write the current in-memory dataset to /data as a seed JSON file.
    Useful if you want to persist a demo dataset.
    """
    if user_id not in _IN_MEMORY:
        raise ValueError(f"No in-memory data for user_id={user_id}")

    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    out_name = filename or f"seed_{user_id}.json"
    out_path = data_dir / out_name

    payload = []
    for r in _IN_MEMORY[user_id]:
        d = asdict(r)
        d["date"] = r.date.isoformat()
        payload.append(d)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return out_path
