"""Generate repeatable energy, closure, failure, and like-for-like reports."""
from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean, stdev

import ortools
from sqlalchemy import select

from ..config import settings
from ..database import SessionLocal
from ..models import AcademicTerm, Room, TimetableSession
from ..optimizer.service import _session_data, solve_energy
from ..optimizer.validator import validate_assignment
from ..routers.optimizer import EnergyRequest
from ..timetable_import import detect_conflicts

REPO_ROOT = Path(__file__).resolve().parents[3]
LAMBDA_GRID = [0.0, 0.1, 0.5, 1.0, 5.0]
RELOCATION_GRID = [0, 5, 10, 20, None]
CLOSURES = [{"floors": [floor]} for floor in range(6)] + [
    {"floors": [1, 2]}, {"floors": [2, 3]},
    {"rooms": ["A-F2-02"]}, {"rooms": ["A-F1-03"]}]
E4_K = (1, 2, 3, 5)
E4_RUNS = 20


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
    saving = 0.0 if not before["kwh_week"] else 100 * (before["kwh_week"] - after["kwh_week"]) / before["kwh_week"]
    return {"kwh_week_before": before["kwh_week"], "kwh_week_after": after["kwh_week"],
            "cost_week_inr_before": before["cost_week_inr"], "cost_week_inr_after": after["cost_week_inr"],
            "percent_saving": round(saving, 6), "relocations": result["relocations"],
            "students_affected": result["affected_students"], "clashes_before": before["clash_count"],
            "clashes_after": after["clash_count"], "solver_status": result["solver_status"],
            "solve_time_s": result["solve_time_s"]}


def _slot_conflicts(sessions: list[dict], assignments: dict[int, str]) -> int:
    mapped = [dict(row, room_id=assignments.get(row["id"], row["room_id"])) for row in sessions]
    return sum(c["type"] == "room" for c in detect_conflicts(mapped))


def _relocations_extra(with_failure: int, no_failure: int) -> int:
    return with_failure - no_failure


def _greedy_first_fit(sessions: list[dict], rooms: list[dict], movable_ids: set[int], strengths: dict[str, int]) -> dict[int, str] | None:
    """Deterministic first-fit, ordered by day, period, section, batch, id."""
    room_map = {r["room_id"]: r for r in rooms}
    assignments = {s["id"]: s["room_id"] for s in sessions if s["room_required"]}
    occupied = {}
    for s in sessions:
        if s["room_required"] and s["id"] not in movable_ids and s["room_id"]:
            for p in range(s["start_period"], s["end_period"] + 1):
                occupied.setdefault((s["room_id"], s["day"], p), []).append(s["id"])
    ordered = sorted((s for s in sessions if s["id"] in movable_ids),
                     key=lambda s: (s["day"], s["start_period"], s["section_code"], s["batch"] or "", s["id"]))
    for s in ordered:
        size = strengths.get(s["section_code"], 0)
        if s["batch"] in {"B1", "B2"}:
            size = (size + 1) // 2
        candidates = []
        for room in rooms:
            typ = room["room_type"].lower()
            lab_room = "lab" in typ or "computer" in typ
            if not room["timetable_eligible"] or room["status"] != "available" or room["capacity_effective"] < size:
                continue
            if s["is_lab"] and not lab_room:
                continue
            if not s["is_lab"] and not any(x in typ for x in ("classroom", "seminar", "lab", "computer")):
                continue
            candidates.append(room)
        for room in sorted(candidates, key=lambda r: r["room_id"]):
            if any(occupied.get((room["room_id"], s["day"], p)) for p in range(s["start_period"], s["end_period"] + 1)):
                continue
            if s["batch"] in {"B1", "B2"} and s["block_id"] and any(
                other["block_id"] == s["block_id"] and other["batch"] in {"B1", "B2"}
                and other["batch"] != s["batch"] and assignments.get(other["id"]) == room["room_id"]
                for other in sessions):
                continue
            assignments[s["id"]] = room["room_id"]
            for p in range(s["start_period"], s["end_period"] + 1):
                occupied.setdefault((room["room_id"], s["day"], p), []).append(s["id"])
            break
        else:
            return None
    return assignments


def run(term_code: str, seeds: list[int], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        term = db.scalar(select(AcademicTerm).where(AcademicTerm.code == term_code))
        if term is None:
            raise ValueError(f"Term not found in configured database: {term_code}")
        sessions, rooms, strengths = _session_data(db, term)
        original_assignments = {s["id"]: s["room_id"] for s in sessions if s["room_required"]}
        movable_ids = {s["id"] for s in sessions if s["room_required"] and s["room_inferred"] and not (s["is_lab"])}

        # Deterministic reports: exactly one run per configuration; the supplied
        # CLI seeds do not create independent trials with one CP-SAT worker.
        e1 = []
        for movable in ("inferred_only", "all"):
            for lock in (True, False):
                res = solve_energy(db, term, EnergyRequest(term=term_code, movable=movable, lock_labs=lock, time_limit_s=30, seed=0))
                e1.append({"movable": movable, "lock_labs": lock, **_metrics(res), "deterministic": True})
        base_cols = ["kwh_week_before", "kwh_week_after", "cost_week_inr_before", "cost_week_inr_after", "percent_saving", "relocations", "students_affected", "clashes_before", "clashes_after", "solver_status", "solve_time_s"]
        _write_csv(out_dir / "E1_energy_baseline_vs_optimized.csv", e1, ["movable", "lock_labs", *base_cols, "deterministic"])

        e2 = []
        for lm in LAMBDA_GRID:
            for limit in RELOCATION_GRID:
                res = solve_energy(db, term, EnergyRequest(term=term_code, movable="inferred_only", lambda_move=lm, max_relocations=limit, time_limit_s=30, seed=0))
                e2.append({"lambda_move": lm, "max_relocations": "none" if limit is None else limit, **_metrics(res), "deterministic": True})
        _write_csv(out_dir / "E2_sensitivity.csv", e2, ["lambda_move", "max_relocations", *base_cols, "deterministic"])

        e3 = []
        for spec in CLOSURES:
            closed_rooms = set(spec.get("rooms", []))
            closed_floors = set(spec.get("floors", []))
            closure_ids = {s["id"] for s in sessions if s["room_required"] and s["room_id"] and
                           (s["room_id"] in closed_rooms or next((r["floor"] for r in rooms if r["room_id"] == s["room_id"]), None) in closed_floors)}
            floor_counts = {f: {"fixed": sum(s["room_required"] and s["id"] not in closure_ids and s["room_id"] and next((r["floor"] for r in rooms if r["room_id"] == s["room_id"]), None) == f for s in sessions),
                                "movable": sum(s["id"] in closure_ids and next((r["floor"] for r in rooms if r["room_id"] == s["room_id"]), None) == f for s in sessions)} for f in range(6)}
            res = solve_energy(db, term, EnergyRequest(term=term_code, movable="inferred_only", close_floors=spec.get("floors", []), close_rooms=spec.get("rooms", []), time_limit_s=30, seed=0))
            assigned = res.get("changes", [])
            optimized_inferred_rooms = {s["id"]: s["room_id"] for s in sessions if s["id"] in movable_ids}
            optimized_inferred_rooms.update({change["session_id"]: change["to_room"] for change in assigned if change["session_id"] in movable_ids})
            by_floor_original = {str(f): sum(1 for s in sessions if s["id"] in closure_ids and next((r["floor"] for r in rooms if r["room_id"] == s["room_id"]), None) == f) for f in range(6)}
            e3.append({"closure": json.dumps(spec, sort_keys=True), "fixed_sessions_by_original_floor": json.dumps(floor_counts, sort_keys=True),
                       "movable_sessions_by_original_floor": json.dumps(by_floor_original, sort_keys=True),
                       "rooms_original_inferred_by_floor": json.dumps({str(f): sorted({s["room_id"] for s in sessions if s["id"] in movable_ids and next((r["floor"] for r in rooms if r["room_id"] == s["room_id"]), None) == f}) for f in range(6)}, sort_keys=True),
                       "rooms_optimised_inferred_by_floor": json.dumps({str(f): sorted({rid for rid in optimized_inferred_rooms.values() if next((r["floor"] for r in rooms if r["room_id"] == rid), None) == f}) for f in range(6)}, sort_keys=True),
                       "feasibility": res["solver_status"] in {"OPTIMAL", "FEASIBLE"}, "relocations": res["relocations"],
                       "kwh_change": round(res["after"]["kwh_week"] - res["before"]["kwh_week"], 6),
                       "unresolvable_reason": res.get("infeasible_reason") or f"fixed_source_clashes={len(res['unresolvable_source_clashes'])}",
                       "solver_status": res["solver_status"], "solve_time_s": res["solve_time_s"]})
        e3_cols = ["closure", "fixed_sessions_by_original_floor", "movable_sessions_by_original_floor", "rooms_original_inferred_by_floor", "rooms_optimised_inferred_by_floor", "feasibility", "relocations", "kwh_change", "unresolvable_reason", "solver_status", "solve_time_s"]
        _write_csv(out_dir / "E3_floor_closure.csv", e3, e3_cols)

        # E4 baseline once per run; RNG seeds are unique and derived per (k, run).
        used = list(db.scalars(select(Room).where(Room.id.in_({s["room_db_id"] for s in sessions if s["room_db_id"]}), Room.timetable_eligible.is_(True))))
        status_orig = {r.id: r.status for r in used}
        e4 = []
        for k in E4_K:
            for run_idx in range(E4_RUNS):
                run_seed = 100000 + k * 100 + run_idx
                baseline = solve_energy(db, term, EnergyRequest(term=term_code, movable="inferred_only", seed=0, time_limit_s=30))
                rng = random.Random(run_seed)
                failed = rng.sample(used, min(k, len(used)))
                try:
                    for room in failed: room.status = "temporarily_unavailable"
                    result = solve_energy(db, term, EnergyRequest(term=term_code, movable="inferred_only", seed=0, time_limit_s=30))
                finally:
                    for room in failed: room.status = status_orig[room.id]
                extra = _relocations_extra(result["relocations"], baseline["relocations"])
                extra_students = max(0, result["affected_students"] - baseline["affected_students"])
                e4.append({"k_rooms_unavailable": k, "run": run_idx, "seed": run_seed,
                           "failed_rooms": json.dumps(sorted(r.number for r in failed)),
                           "relocations_no_failure": baseline["relocations"], "relocations_with_failure": result["relocations"],
                           "relocations_extra": extra, "extra_students_affected": extra_students,
                           "solver_status": result["solver_status"], "solve_time_s": result["solve_time_s"]})
        _write_csv(out_dir / "E4_random_room_failure.csv", e4, ["k_rooms_unavailable", "run", "seed", "failed_rooms", "relocations_no_failure", "relocations_with_failure", "relocations_extra", "extra_students_affected", "solver_status", "solve_time_s"])
        e4_summary = []
        for k in E4_K:
            rows = [r for r in e4 if r["k_rooms_unavailable"] == k]
            valid = [r for r in rows if r["solver_status"] in {"OPTIMAL", "FEASIBLE"}]
            e4_summary.append({"k_rooms_unavailable": k, "runs": len(rows), "feasibility_rate": len(valid) / len(rows),
                "mean_relocations_extra": fmean(r["relocations_extra"] for r in valid) if valid else "",
                "std_relocations_extra": stdev(r["relocations_extra"] for r in valid) if len(valid) > 1 else 0,
                "mean_extra_students_affected": fmean(r["extra_students_affected"] for r in valid) if valid else "",
                "std_extra_students_affected": stdev(r["extra_students_affected"] for r in valid) if len(valid) > 1 else 0,
                "mean_solve_time_s": fmean(r["solve_time_s"] for r in rows)})
        _write_csv(out_dir / "E4_summary.csv", e4_summary, list(e4_summary[0]))

        # E5 strategies share the same inferred non-lab movable set. Existing
        # fixed room clashes are a hard obstruction to a globally clash-free row.
        fixed_clash_count = _slot_conflicts(sessions, original_assignments)
        strategies = ["greedy_first_fit", "cp_sat_min_relocations", "cp_sat_energy_aware"]
        e5 = []
        greedy = _greedy_first_fit(sessions, rooms, movable_ids, strengths)
        optimizer0 = solve_energy(db, term, EnergyRequest(term=term_code, movable="inferred_only", lambda_move=1, lambda_floor=0, seed=0, time_limit_s=30), energy_weight=0)
        optimizer1 = solve_energy(db, term, EnergyRequest(term=term_code, movable="inferred_only", lambda_move=1, lambda_floor=0, seed=0, time_limit_s=30), energy_weight=1)
        for strategy, assignment, result in [(strategies[0], greedy, None), (strategies[1], None, optimizer0), (strategies[2], None, optimizer1)]:
            if result is not None:
                assignment = {s["id"]: s["room_id"] for s in sessions if s["room_required"]}
                assignment.update({ch["session_id"]: ch["to_room"] for ch in result["changes"]})
            valid = assignment is not None and validate_assignment(sessions, rooms, assignment, movable_ids=movable_ids, section_strengths=strengths)["valid"]
            clashes = _slot_conflicts(sessions, assignment or original_assignments)
            # Source-fixed clashes are preserved by the validator, but make the
            # required all-session clash-free comparison infeasible.
            feasible = bool(valid and clashes == 0)
            reloc = sum(assignment.get(sid) != original_assignments.get(sid) for sid in movable_ids) if assignment else ""
            e5.append({"strategy": strategy, "kwh_week": "", "cost_week_inr": "", "rooms_used": "", "floors_used": "",
                       "relocations_vs_original": reloc, "students_affected": "", "solver_status": "FEASIBLE" if feasible else "INFEASIBLE",
                       "solve_time_s": result["solve_time_s"] if result else 0,
                       "reason": f"fixed source room clashes prevent clash-free timetable (count={fixed_clash_count})" if not feasible else ""})
        baseline_energy = solve_energy(db, term, EnergyRequest(term=term_code, movable="inferred_only", seed=0, time_limit_s=30))
        e5.append({"strategy": "baseline_with_clashes_not_comparable", "kwh_week": baseline_energy["before"]["kwh_week"],
                   "cost_week_inr": baseline_energy["before"]["cost_week_inr"], "rooms_used": len(set(original_assignments.values())),
                   "floors_used": len({next(r["floor"] for r in rooms if r["room_id"] == rid) for rid in original_assignments.values()}),
                   "relocations_vs_original": 0, "students_affected": 0, "solver_status": "NOT_COMPARABLE",
                   "solve_time_s": 0, "reason": f"original assignment contains {fixed_clash_count} room clashes"})
        e5_cols = ["strategy", "kwh_week", "cost_week_inr", "rooms_used", "floors_used", "relocations_vs_original", "students_affected", "solver_status", "solve_time_s", "reason"]
        _write_csv(out_dir / "E5_clash_free_strategies.csv", e5, e5_cols)
        sweep = []
        for weight in (0, 0.25, 0.5, 1, 2):
            res = solve_energy(db, term, EnergyRequest(term=term_code, movable="inferred_only", lambda_move=1, lambda_floor=0, seed=0, time_limit_s=30), energy_weight=weight)
            sweep.append({"energy_weight": weight, "solver_status": res["solver_status"], "kwh_week_after": res["after"]["kwh_week"], "relocations": res["relocations"], "clashes_after": res["after"]["clash_count"], "solve_time_s": res["solve_time_s"]})
        _write_csv(out_dir / "E5_energy_weight_sensitivity.csv", sweep, list(sweep[0]))

    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        commit = "unavailable"
    manifest = {"git_commit_hash": commit, "ortools_version": ortools.__version__, "python_version": platform.python_version(),
        "seeds": {"E1_E2_E3": "deterministic; seed=0; num_workers=1", "E4": "derived independently per (k, run)"},
        "settings": {"period_hours": settings.period_hours, "standby_fraction": settings.standby_fraction,
            "periods_per_day": settings.periods_per_day, "tariff_inr_per_kwh": settings.energy_tariff_inr_per_kwh,
            "lambda_move_grid": LAMBDA_GRID, "max_relocations_grid": RELOCATION_GRID, "closures": CLOSURES,
            "e4_runs_per_k": E4_RUNS, "time_limit_s": 30, "num_workers": 1, "e5_energy_weights": [0, .25, .5, 1, 2]},
        "term": term_code, "data_status_notes": ["Synthetic equipment wattages and tariff.", "Inferred timetable room assignments; source conflicts remain reported.", "No real DSATM meter readings are available."],
        "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote E1 ({len(e1)} rows), E2 ({len(e2)} rows), E3 ({len(e3)} rows), E4 ({len(e4)} runs), E5 ({len(e5)} rows), and manifest.json to {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--term", required=True)
    parser.add_argument("--seeds", nargs="+", type=int, required=True, help="accepted for compatibility; E1-E3 are deterministic")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    run(args.term, args.seeds, _out_dir(args.out))


if __name__ == "__main__":
    main()
