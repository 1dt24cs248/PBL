"""Generate repeatable energy, closure, failure, and like-for-like reports."""
from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import re
import subprocess
from collections import Counter, defaultdict
from time import perf_counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean, stdev

import ortools
from sqlalchemy import select

from ..config import settings
from ..database import SessionLocal
from ..energy import calculate_energy
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
E6_VARIANTS = {
    "V1_inferred_theory": ("inferred_only", True),
    "V2_all_theory": ("all", True),
    "V3_all_theory_and_labs": ("all", False),
}
E6_COLUMNS = ["variant", "strategy", "kwh_week", "cost_week_inr", "rooms_used", "floors_used",
              "relocations", "students_affected", "new_clashes", "fixed_clashes_remaining",
              "solver_status", "solve_time_s", "objective_value"]


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


def _assignment(result: dict, sessions: list[dict]) -> dict[int, str]:
    assigned = {s["id"]: s["room_id"] for s in sessions if s["room_required"]}
    assigned.update({change["session_id"]: change["to_room"] for change in result["changes"]})
    return assigned


def _room_on_energy(assignments: dict[int, str], sessions: list[dict], rooms: list[dict]) -> float:
    room_by_id = {room["room_id"]: room for room in rooms}
    on = set()
    for session in sessions:
        room_id = assignments.get(session["id"])
        if session["room_required"] and room_id:
            on.update((room_id, session["day"], period)
                      for period in range(session["start_period"], session["end_period"] + 1))
    scale = 10000
    return sum(round(room_by_id[room_id]["connected_kw"] * settings.period_hours *
                     settings.energy_tariff_inr_per_kwh * scale) / scale
               for room_id, _day, _period in on)


def _objective_value(assignments: dict[int, str], sessions: list[dict], rooms: list[dict],
                     movable_ids: set[int], original: dict[int, str], energy_weight: float,
                     lambda_move: float = 1.0) -> float:
    return round(energy_weight * _room_on_energy(assignments, sessions, rooms) +
                 lambda_move * sum(assignments.get(sid) != original.get(sid) for sid in movable_ids), 4)


def _closed_ids(sessions: list[dict], rooms: list[dict], closure: dict) -> set[int]:
    room_floors = {r["room_id"]: r["floor"] for r in rooms}
    floors, closed_rooms = set(closure.get("floors", [])), set(closure.get("rooms", []))
    return {s["id"] for s in sessions if s["room_required"] and s["room_id"] and
            (s["room_id"] in closed_rooms or room_floors.get(s["room_id"]) in floors)}


def _candidate_room_domain_sizes(sessions: list[dict], rooms: list[dict], movable_ids: set[int]) -> list[int]:
    fixed_occupancy = defaultdict(set)
    for session in sessions:
        if session["room_required"] and session["id"] not in movable_ids and session["room_id"]:
            for period in range(session["start_period"], session["end_period"] + 1):
                fixed_occupancy[(session["day"], period)].add(session["room_id"])
    sizes = []
    for session in sessions:
        if session["id"] not in movable_ids:
            continue
        if not session["section_strength_known"]:
            sizes.append(0)
            continue
        compatible = []
        for room in rooms:
            kind = room["room_type"].lower()
            is_lab_room = "lab" in kind or "computer" in kind
            if not room["timetable_eligible"] or room["status"] != "available":
                continue
            if session["is_lab"] and not is_lab_room:
                continue
            if not session["is_lab"] and not any(token in kind for token in ("classroom", "seminar", "lab", "computer")):
                continue
            needed = session["section_strength"]
            if session["batch"] in {"B1", "B2"}:
                needed = (needed + 1) // 2
            if room["capacity_effective"] < needed:
                continue
            if any(room["room_id"] in fixed_occupancy[(session["day"], period)]
                   for period in range(session["start_period"], session["end_period"] + 1)):
                continue
            compatible.append(room["room_id"])
        sizes.append(len(compatible))
    return sizes


def _closure_failure_details(sessions: list[dict], rooms: list[dict], closed_ids: set[int],
                             closure: dict, lock_labs: bool, result: dict) -> str:
    if result["solver_status"] not in {"INFEASIBLE", "MODEL_INVALID"}:
        return "[]"
    closed_floors, closed_rooms = set(closure.get("floors", [])), set(closure.get("rooms", []))
    details = []
    reason_text = result.get("infeasible_reason") or ""
    no_room_ids = {int(value) for value in re.findall(r"session (\d+) has no eligible room", reason_text)}
    for row in sessions:
        if row["id"] not in closed_ids:
            continue
        kind = "lab" if row["is_lab"] else "theory"
        if row["is_lab"] and lock_labs:
            reason = "lab is locked by lock_labs=true and cannot leave the closed room/floor"
        elif row["id"] in no_room_ids:
            reason = "no available eligible destination meets lab/theory type and effective-capacity constraints"
        else:
            reason = "joint room-slot constraints leave no complete assignment for this session type"
        details.append({"session_id": row["id"], "session_type": kind, "reason": reason})
    return json.dumps(details, sort_keys=True)


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
        source_conflicts = detect_conflicts(sessions)
        source_conflict_counts = Counter(conflict["type"] for conflict in source_conflicts)
        involved_indexes = {index for conflict in source_conflicts for index in conflict["session_indices"]}
        free_movable_count = sum(session["id"] in movable_ids and index not in involved_indexes
                                 for index, session in enumerate(sessions))
        v1_domain_sizes = _candidate_room_domain_sizes(sessions, rooms, movable_ids)
        v1_domain_counts = Counter(v1_domain_sizes)

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
            closure_ids = _closed_ids(sessions, rooms, spec)
            floor_counts = {f: {"fixed": sum(s["room_required"] and s["id"] not in closure_ids and s["room_id"] and next((r["floor"] for r in rooms if r["room_id"] == s["room_id"]), None) == f for s in sessions),
                                "movable": sum(s["id"] in closure_ids and next((r["floor"] for r in rooms if r["room_id"] == s["room_id"]), None) == f for s in sessions)} for f in range(6)}
            for lock_labs in (True, False):
                res = solve_energy(db, term, EnergyRequest(term=term_code, movable="inferred_only", lock_labs=lock_labs,
                    close_floors=spec.get("floors", []), close_rooms=spec.get("rooms", []), time_limit_s=30, seed=0))
                assigned = res.get("changes", [])
                optimized_inferred_rooms = {s["id"]: s["room_id"] for s in sessions if s["id"] in movable_ids}
                optimized_inferred_rooms.update({change["session_id"]: change["to_room"] for change in assigned if change["session_id"] in movable_ids})
                by_floor_original = {str(f): sum(1 for s in sessions if s["id"] in closure_ids and next((r["floor"] for r in rooms if r["room_id"] == s["room_id"]), None) == f) for f in range(6)}
                e3.append({"closure": json.dumps(spec, sort_keys=True), "lock_labs": lock_labs,
                           "fixed_sessions_by_original_floor": json.dumps(floor_counts, sort_keys=True),
                           "movable_sessions_by_original_floor": json.dumps(by_floor_original, sort_keys=True),
                           "rooms_original_inferred_by_floor": json.dumps({str(f): sorted({s["room_id"] for s in sessions if s["id"] in movable_ids and next((r["floor"] for r in rooms if r["room_id"] == s["room_id"]), None) == f}) for f in range(6)}, sort_keys=True),
                           "rooms_optimised_inferred_by_floor": json.dumps({str(f): sorted({rid for rid in optimized_inferred_rooms.values() if next((r["floor"] for r in rooms if r["room_id"] == rid), None) == f}) for f in range(6)}, sort_keys=True),
                           "feasibility": res["solver_status"] in {"OPTIMAL", "FEASIBLE"}, "relocations": res["relocations"],
                           "kwh_change": round(res["after"]["kwh_week"] - res["before"]["kwh_week"], 6),
                           "unresolvable_reason": res.get("infeasible_reason") or f"fixed_source_clashes={len(res['unresolvable_source_clashes'])}",
                           "infeasible_session_details": _closure_failure_details(sessions, rooms, closure_ids, spec, lock_labs, res),
                           "solver_status": res["solver_status"], "solve_time_s": res["solve_time_s"]})
        e3_cols = ["closure", "lock_labs", "fixed_sessions_by_original_floor", "movable_sessions_by_original_floor", "rooms_original_inferred_by_floor", "rooms_optimised_inferred_by_floor", "feasibility", "relocations", "kwh_change", "unresolvable_reason", "infeasible_session_details", "solver_status", "solve_time_s"]
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

        e6 = []
        reference_validation = validate_assignment(sessions, rooms, original_assignments,
            movable_ids=movable_ids, section_strengths=strengths, lock_labs=True, no_new_clashes=True)
        reference_energy = calculate_energy(db, term, assignments={
            db_id: next(r["db_id"] for r in rooms if r["room_id"] == room_id)
            for db_id, room_id in original_assignments.items()})["timetable_occupancy"]["block"]
        reference_room_ids = set(original_assignments.values())
        reference_floors = {next(r["floor"] for r in rooms if r["room_id"] == room_id) for room_id in reference_room_ids}
        e6.append({"variant": "V1_inferred_theory", "strategy": "original_inferred",
            "kwh_week": reference_energy["kwh_week"], "cost_week_inr": reference_energy["cost_week_inr"],
            "rooms_used": len(reference_room_ids), "floors_used": len(reference_floors), "relocations": 0,
            "students_affected": 0, "new_clashes": len(reference_validation["new_clashes"]),
            "fixed_clashes_remaining": reference_validation["fixed_clashes_remaining"],
            "solver_status": "REFERENCE_HAS_CLASHES" if reference_validation["new_clashes"] or reference_validation["fixed_clashes_remaining"] else "REFERENCE_VALID",
            "solve_time_s": 0.0, "objective_value": _objective_value(original_assignments, sessions, rooms,
                movable_ids, original_assignments, energy_weight=1)})

        for variant, (movable_mode, lock_labs) in E6_VARIANTS.items():
            variant_movable = {s["id"] for s in sessions if s["room_required"] and
                ((movable_mode == "all") or (movable_mode == "inferred_only" and s["room_inferred"])) and
                (not s["is_lab"] or not lock_labs)}
            strategies = [("greedy_first_fit", "greedy", None, None)]
            strategies.append(("cp_sat_min_relocations", "cp", 0.0, None))
            strategies.append(("cp_sat_energy_aware", "cp", 1.0, None))
            strategies.extend((f"cp_sat_energy_relocation_budget_{budget}", "cp", 1.0, budget)
                              for budget in (0, 5, 10, 20))
            baseline_fixed = validate_assignment(sessions, rooms, original_assignments,
                movable_ids=variant_movable, section_strengths=strengths, lock_labs=lock_labs,
                no_new_clashes=True)["fixed_clashes_remaining"]
            for strategy, kind, weight, relocation_budget in strategies:
                started = perf_counter()
                solver_result = None
                if kind == "greedy":
                    assignment = _greedy_first_fit(sessions, rooms, variant_movable, strengths)
                    solver_status = "FEASIBLE" if assignment is not None else "INFEASIBLE"
                    energy_weight = 1.0
                    solver_time = perf_counter() - started
                else:
                    request = EnergyRequest(term=term_code, movable=movable_mode, lock_labs=lock_labs,
                        lambda_move=1.0, lambda_floor=0.0, max_relocations=relocation_budget,
                        seed=0, time_limit_s=30)
                    solver_result = solve_energy(db, term, request, energy_weight=weight)
                    solver_status = solver_result["solver_status"]
                    assignment = _assignment(solver_result, sessions) if solver_status in {"OPTIMAL", "FEASIBLE"} else None
                    energy_weight = weight
                    solver_time = solver_result["solve_time_s"]

                if assignment is None:
                    row = {"variant": variant, "strategy": strategy, "kwh_week": "", "cost_week_inr": "",
                           "rooms_used": "", "floors_used": "", "relocations": "", "students_affected": "",
                           "new_clashes": "", "fixed_clashes_remaining": baseline_fixed,
                           "solver_status": solver_status, "solve_time_s": round(solver_time, 6),
                           "objective_value": ""}
                else:
                    validation = validate_assignment(sessions, rooms, assignment,
                        movable_ids=variant_movable, section_strengths=strengths,
                        max_relocations=relocation_budget, lock_labs=lock_labs, no_new_clashes=True)
                    if not validation["valid"]:
                        solver_status = "INVALID_ASSIGNMENT"
                    db_assignments = {db_id: next(r["db_id"] for r in rooms if r["room_id"] == room_id)
                                      for db_id, room_id in assignment.items() if room_id is not None}
                    energy = calculate_energy(db, term, assignments=db_assignments)["timetable_occupancy"]["block"]
                    used_room_ids = {room_id for room_id in assignment.values() if room_id}
                    room_by_id = {room["room_id"]: room for room in rooms}
                    changed = {sid for sid in variant_movable if assignment.get(sid) != original_assignments.get(sid)}
                    affected_sections = {s["section_code"] for s in sessions if s["id"] in changed}
                    affected_students = sum(strengths.get(section, 0) for section in affected_sections)
                    objective = (solver_result["objective_value"] if solver_result is not None and solver_status in {"OPTIMAL", "FEASIBLE"}
                                 else _objective_value(assignment, sessions, rooms, variant_movable,
                                                       original_assignments, energy_weight))
                    row = {"variant": variant, "strategy": strategy, "kwh_week": energy["kwh_week"],
                           "cost_week_inr": energy["cost_week_inr"], "rooms_used": len(used_room_ids),
                           "floors_used": len({room_by_id[rid]["floor"] for rid in used_room_ids}),
                           "relocations": len(changed), "students_affected": affected_students,
                           "new_clashes": len(validation["new_clashes"]),
                           "fixed_clashes_remaining": validation["fixed_clashes_remaining"],
                           "solver_status": solver_status, "solve_time_s": round(solver_time, 6),
                           "objective_value": objective}
                e6.append(row)
        _write_csv(out_dir / "E6_energy_comparison.csv", e6, E6_COLUMNS)

        e6_sensitivity = []
        for weight in (0, 0.25, 0.5, 1, 2):
            req = EnergyRequest(term=term_code, movable="inferred_only", lock_labs=True,
                                lambda_move=1, lambda_floor=0, seed=0, time_limit_s=30)
            res = solve_energy(db, term, req, energy_weight=weight)
            assigned = _assignment(res, sessions) if res["solver_status"] in {"OPTIMAL", "FEASIBLE"} else original_assignments
            movable_ids_v1 = {s["id"] for s in sessions if s["room_required"] and s["room_inferred"] and not s["is_lab"]}
            relocation_term = sum(assigned.get(sid) != original_assignments.get(sid) for sid in movable_ids_v1)
            energy_component = weight * _room_on_energy(assigned, sessions, rooms)
            e6_sensitivity.append({"energy_weight": weight, "solver_status": res["solver_status"],
                "objective_value": res["objective_value"], "energy_term": round(energy_component, 4),
                "relocation_term": relocation_term, "floor_term": 0,
                "kwh_week": res["after"]["kwh_week"], "relocations": res["relocations"],
                "assignment_signature": ";".join(f"{sid}:{assigned.get(sid)}" for sid in sorted(movable_ids_v1))})
        _write_csv(out_dir / "E6_energy_weight_sensitivity.csv", e6_sensitivity,
                   ["energy_weight", "solver_status", "objective_value", "energy_term", "relocation_term", "floor_term", "kwh_week", "relocations", "assignment_signature"])

    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        commit = "unavailable"
    manifest = {"git_commit_hash": commit, "ortools_version": ortools.__version__, "python_version": platform.python_version(),
        "seeds": {"E1_E3_E5_E6": "deterministic; seed=0; num_workers=1", "E4": "derived independently per (k, run)"},
        "settings": {"period_hours": settings.period_hours, "standby_fraction": settings.standby_fraction,
            "periods_per_day": settings.periods_per_day, "tariff_inr_per_kwh": settings.energy_tariff_inr_per_kwh,
            "lambda_move_grid": LAMBDA_GRID, "max_relocations_grid": RELOCATION_GRID, "closures": CLOSURES,
            "e3_lock_labs_variants": [True, False], "e4_runs_per_k": E4_RUNS, "time_limit_s": 30,
            "num_workers": 1, "e5_energy_weights": [0, .25, .5, 1, 2],
            "e6_variants": list(E6_VARIANTS), "e6_relocation_budgets": [0, 5, 10, 20],
            "e6_energy_weights": [0, .25, .5, 1, 2], "e6_no_new_clash_validation": True},
        "term": term_code, "audit_metrics": {"active_term_sessions": len(sessions), "v1_movable_sessions": len(movable_ids),
            "v1_sessions_with_multiple_feasible_rooms": sum(size > 1 for size in v1_domain_sizes),
            "v1_free_of_all_source_conflicts": free_movable_count,
            "v1_feasible_room_domain_counts": {str(size): count for size, count in sorted(v1_domain_counts.items())},
            "source_conflicts_by_type": dict(source_conflict_counts)},
        "data_status_notes": ["Synthetic equipment wattages and Rs 8.50/kWh tariff.",
            "Requested source summary reports 317/463 inferred-room sessions; current parser measured 323/475.",
            "Fixed source room/faculty conflicts are retained and reported; room-only assignment does not change faculty or section overlap.",
            "SQLite only; PostgreSQL unverified.", "No real DSATM meter readings are available."],
        "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote E1 ({len(e1)} rows), E2 ({len(e2)} rows), E3 ({len(e3)} rows), E4 ({len(e4)} runs), E5 ({len(e5)} rows), E6 ({len(e6)} rows), and manifest.json to {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--term", required=True)
    parser.add_argument("--seeds", nargs="+", type=int, required=True, help="accepted for compatibility; E1-E3 are deterministic")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    run(args.term, args.seeds, _out_dir(args.out))


if __name__ == "__main__":
    main()
