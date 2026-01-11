from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import List


@dataclass
class SeedDay:
    date: str
    recovery_value: float
    sleep_duration: float
    sleep_consistency: float
    excercise_data_point: float
    nutrition_data_point: float  


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def iso_days(n_days: int, end: date | None = None) -> List[date]:
    end = end or date.today()
    start = end - timedelta(days=n_days - 1)
    return [start + timedelta(days=i) for i in range(n_days)]


def gen_stable(n_days: int, seed: int = 7) -> List[SeedDay]:
    """
    Stable timeline: low variance, few/no meaningful dips.
    """
    rng = random.Random(seed)

    # Personal baselines
    base_sleep = 7.7
    base_cons = 0.86
    base_ex = 520.0
    base_nut = 2300.0  
    base_rec = 82.0

    days = []
    for d in iso_days(n_days):
        sleep = clamp(rng.gauss(base_sleep, 0.25), 6.5, 9.0)
        cons = clamp(rng.gauss(base_cons, 0.04), 0.65, 0.98)
        ex = clamp(rng.gauss(base_ex, 55.0), 350, 750)
        nut = clamp(rng.gauss(base_nut, 150.0), 1600, 2800)  

        # Recovery: mild sensitivity, mostly stable
        rec = base_rec
        rec += (sleep - base_sleep) * 1.3
        rec += (cons - base_cons) * 10.0
        rec += (nut - base_nut) / 100.0  
        rec += -abs(ex - base_ex) / 220.0
        rec += rng.gauss(0, 1.2)

        days.append(
            SeedDay(
                date=d.isoformat(),
                recovery_value=clamp(rec, 55, 97),
                sleep_duration=round(sleep, 2),
                sleep_consistency=round(cons, 3),
                excercise_data_point=round(ex, 1),
                nutrition_data_point=round(nut, 0),  
            )
        )
    return days


def gen_exercise_factor(n_days: int, seed: int = 11) -> List[SeedDay]:
    """
    Exercise-driven dips: exercise load spikes create dips.
    We keep sleep/nutrition mostly normal, but on some dip days,
    nutrition lags slightly to reflect "context-dependent" exercise.
    """
    rng = random.Random(seed)

    base_sleep = 7.6
    base_cons = 0.84
    base_ex = 500.0
    base_nut = 2250.0  
    base_rec = 81.0

    dip_days = set()
    # 7 dip clusters spaced out
    starts = [8, 16, 23, 31, 38, 46, 54]
    for s in starts:
        dip_days.add(s)  # single-day dip marker

    days = []
    all_dates = iso_days(n_days)
    for i, d in enumerate(all_dates):
        sleep = clamp(rng.gauss(base_sleep, 0.30), 6.0, 9.0)
        cons = clamp(rng.gauss(base_cons, 0.05), 0.60, 0.98)
        nut = clamp(rng.gauss(base_nut, 180.0), 1500, 2900)  

        ex = clamp(rng.gauss(base_ex, 60.0), 300, 760)

        # Exercise dip: spike load
        if i in dip_days:
            ex = clamp(rng.gauss(base_ex + 260, 45.0), 650, 900)

            # On ~half of exercise dips, nutrition is slightly worse (fueling mismatch)
            if rng.random() < 0.55:
                nut = clamp(nut - rng.uniform(250, 450), 1200, 2900) 

        # Recovery sensitivity favors exercise deviations
        rec = base_rec
        rec += (sleep - base_sleep) * 1.0
        rec += (cons - base_cons) * 8.0
        rec += (nut - base_nut) / 100.0 

        # exercise deviation penalty stronger here
        rec += -(abs(ex - base_ex) / 120.0)
        rec += rng.gauss(0, 1.4)

        days.append(
            SeedDay(
                date=d.isoformat(),
                recovery_value=clamp(rec, 45, 97),
                sleep_duration=round(sleep, 2),
                sleep_consistency=round(cons, 3),
                excercise_data_point=round(ex, 1),
                nutrition_data_point=round(nut, 0),  
            )
        )
    return days


def gen_sleep_factor(n_days: int, seed: int = 19) -> List[SeedDay]:
    """
    Sleep-driven dips: sleep duration/consistency drop drives dips.
    Exercise stays mostly normal.
    """
    rng = random.Random(seed)

    base_sleep = 7.8
    base_cons = 0.87
    base_ex = 510.0
    base_nut = 2080.0  
    base_rec = 83.0

    dip_days = set()
    starts = [10, 18, 27, 35, 43, 52]
    for s in starts:
        dip_days.add(s)
        dip_days.add(s + 1)  # a few 2-day sleep debt runs

    days = []
    all_dates = iso_days(n_days)
    for i, d in enumerate(all_dates):
        ex = clamp(rng.gauss(base_ex, 55.0), 330, 720)
        nut = clamp(rng.gauss(base_nut, 170.0), 1550, 2850)  

        sleep = clamp(rng.gauss(base_sleep, 0.25), 6.5, 9.2)
        cons = clamp(rng.gauss(base_cons, 0.04), 0.65, 0.98)

        if i in dip_days:
            # sleep debt / inconsistency
            sleep = clamp(rng.gauss(base_sleep - 1.6, 0.35), 4.5, 7.0)
            cons = clamp(rng.gauss(base_cons - 0.16, 0.06), 0.45, 0.85)

        # Recovery sensitivity favors sleep
        rec = base_rec
        rec += (sleep - base_sleep) * 2.2
        rec += (cons - base_cons) * 14.0
        rec += (nut - base_nut) / 100.0  
        rec += -abs(ex - base_ex) / 260.0
        rec += rng.gauss(0, 1.3)

        days.append(
            SeedDay(
                date=d.isoformat(),
                recovery_value=clamp(rec, 45, 97),
                sleep_duration=round(sleep, 2),
                sleep_consistency=round(cons, 3),
                excercise_data_point=round(ex, 1),
                nutrition_data_point=round(nut, 0),  
            )
        )
    return days


def write_seed(path: Path, rows: List[SeedDay]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in rows], f, indent=2)
    print(f"Wrote {path} ({len(rows)} days)")


def main() -> None:
    n_days = 60  
    out_dir = Path("data")

    write_seed(out_dir / "seed_stable1.json", gen_stable(n_days))
    write_seed(out_dir / "seed_exercise1.json", gen_exercise_factor(n_days))
    write_seed(out_dir / "seed_sleep1.json", gen_sleep_factor(n_days))


if __name__ == "__main__":
    main()