"""Run deterministic M6 energy optimizer experiment sweeps and write raw CSVs."""
from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean

import ortools
from sqlalchemy import select

from ..config import settings
from ..database import SessionLocal
from ..models import AcademicTerm, Room, TimetableSession
from ..optimizer.service import solve_energy
from ..routers.optimizer import EnergyRequest

REPO_ROOT = Path(__file__).resolve().parents[3]
LAMBDA_GRID = [0.0, 0.1, 0.5, 1.0, 5.0]
RELOCATION_GRID = [0, 5, 10, 20, None]
FLOOR_SCENARIOS = [[5], [4], [4, 5], [5, 3]]


def _out_dir(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    if Path.cwd() == REPO_ROOT / "backend" and path.parts and path.parts[0].lower() == "backend":
        return REPO_ROOT / path
    return Path.cwd() / path


def _write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _metrics(result: dict) -> dict:
    before, after = result["before"], result["after"]
    savings = 0.0 if not before["kwh_week"] else 100 * (before["kwh_week"] - after["kwh_week"]) / before["kwh_week"]
    return {"kwh_week_before": before["kwh_week"], "kwh_week_after": after["kwh_week"],
            "cost_week_inr_before": before["cost_week_inr"], "cost_week_inr_after": after["cost_week_inr"],
            "percent_saving": round(savings, 6), "relocations": result["relocations"],
            "students_affected": result["affected_students"], "clashes_before": before["clash_count"],
            "clashes_after": after["clash_count"], "solver_status": result["solver_status"],
            "solve_time_s": result["solve_time_s"]}


def run(term_code: str, seeds: list[int], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        term = db.scalar(select(AcademicTerm).where(AcademicTerm.code == term_code))
        if term is None:
            raise ValueError(f"Term not found in configured database: {term_code}")

        e1 = []
        for movable in ("inferred_only", "all"):
            for lock_labs in (True, False):
                for seed in seeds:
                    result = solve_energy(db, term, EnergyRequest(term=term_code, movable=movable,
                        lock_labs=lock_labs, time_limit_s=30, seed=seed))
                    e1.append({"seed": seed, "movable": movable, "lock_labs": lock_labs, **_metrics(result)})
        e1_cols = ["seed", "movable", "lock_labs", "kwh_week_before", "kwh_week_after", "cost_week_inr_before",
                   "cost_week_inr_after", "percent_saving", "relocations", "students_affected", "clashes_before",
                   "clashes_after", "solver_status", "solve_time_s"]
        _write_csv(out_dir / "E1_energy_baseline_vs_optimized.csv", e1, e1_cols)

        e2 = []
        for lambda_move in LAMBDA_GRID:
            for max_relocations in RELOCATION_GRID:
                for seed in seeds:
                    result = solve_energy(db, term, EnergyRequest(term=term_code, movable="inferred_only",
                        max_relocations=max_relocations, lambda_move=lambda_move, time_limit_s=30, seed=seed))
                    e2.append({"seed": seed, "lambda_move": lambda_move, "max_relocations": max_relocations,
                               **_metrics(result)})
        e2_cols = ["seed", "lambda_move", "max_relocations", *e1_cols[3:]]
        _write_csv(out_dir / "E2_sensitivity.csv", e2, e2_cols)

        e3 = []
        for floors in FLOOR_SCENARIOS:
            for seed in seeds:
                result = solve_energy(db, term, EnergyRequest(term=term_code, movable="inferred_only",
                    forbid_floors=floors, time_limit_s=30, seed=seed))
                metric = _metrics(result)
                e3.append({"seed": seed, "forbid_floors": json.dumps(floors),
                    "feasibility": result["solver_status"] in {"OPTIMAL", "FEASIBLE"},
                    "relocations": result["relocations"], "kwh_change": metric["kwh_week_after"] - metric["kwh_week_before"],
                    "unresolvable_reason": result.get("infeasible_reason") or f"fixed_source_clashes={len(result['unresolvable_source_clashes'])}",
                    "solver_status": result["solver_status"], "solve_time_s": result["solve_time_s"]})
        _write_csv(out_dir / "E3_floor_closure.csv", e3,
            ["seed", "forbid_floors", "feasibility", "relocations", "kwh_change", "unresolvable_reason", "solver_status", "solve_time_s"])

        used_room_ids = set(db.scalars(select(TimetableSession.room_id).where(
            TimetableSession.term_id == term.id, TimetableSession.room_id.is_not(None))))
        eligible_used = list(db.scalars(select(Room).where(Room.id.in_(used_room_ids), Room.timetable_eligible.is_(True))))
        original_status = {room.id: room.status for room in eligible_used}
        runs: dict[int, list[dict]] = {k: [] for k in (1, 2, 3, 5)}
        baseline_by_seed = {seed: solve_energy(db, term, EnergyRequest(term=term_code,
            movable="inferred_only", time_limit_s=30, seed=seed)) for seed in seeds}
        for k in runs:
            for seed in seeds:
                rng = random.Random(seed)
                unavailable = rng.sample(eligible_used, min(k, len(eligible_used))) if eligible_used else []
                for room in unavailable:
                    room.status = "temporarily_unavailable"
                result = solve_energy(db, term, EnergyRequest(term=term_code, movable="inferred_only",
                    time_limit_s=30, seed=seed))
                for room in unavailable:
                    room.status = original_status[room.id]
                result["extra_students_affected"] = max(0, result["affected_students"] - baseline_by_seed[seed]["affected_students"])
                runs[k].append(result)
        e4 = []
        for k, results in runs.items():
            feasible = [row for row in results if row["solver_status"] in {"OPTIMAL", "FEASIBLE"}]
            e4.append({"k_rooms_unavailable": k, "runs": len(results),
                "feasibility_rate": len(feasible) / len(results) if results else 0,
                "mean_relocations": fmean(row["relocations"] for row in feasible) if feasible else "",
                "mean_extra_students_affected": fmean(row["extra_students_affected"] for row in feasible) if feasible else "",
                "mean_solve_time_s": fmean(row["solve_time_s"] for row in results) if results else ""})
        _write_csv(out_dir / "E4_random_room_failure.csv", e4,
            ["k_rooms_unavailable", "runs", "feasibility_rate", "mean_relocations", "mean_extra_students_affected", "mean_solve_time_s"])

    try:
        commit_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        commit_hash = "unavailable"
    manifest = {"git_commit_hash": commit_hash, "ortools_version": ortools.__version__,
        "python_version": platform.python_version(), "seeds": seeds,
        "settings": {"period_hours": settings.period_hours, "standby_fraction": settings.standby_fraction,
            "periods_per_day": settings.periods_per_day, "tariff_inr_per_kwh": settings.energy_tariff_inr_per_kwh,
            "lambda_move_grid": LAMBDA_GRID, "max_relocations_grid": RELOCATION_GRID,
            "floor_scenarios": FLOOR_SCENARIOS, "time_limit_s": 30, "num_workers": 1},
        "term": term_code, "data_status_notes": ["Synthetic equipment wattages and tariff.",
            "Imported and inferred timetable room assignments; source conflicts remain reported.",
            "No real DSATM meter readings are available."],
        "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote E1 ({len(e1)} records), E2 ({len(e2)} records), E3 ({len(e3)} records), E4 ({sum(len(r) for r in runs.values())} runs), and manifest.json to {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--term", required=True)
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    run(args.term, args.seeds, _out_dir(args.out))


if __name__ == "__main__":
    main()
