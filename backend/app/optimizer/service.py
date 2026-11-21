"""CP-SAT energy optimizer. The result is a draft; this module never writes sessions."""
from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from time import perf_counter

from ortools.sat.python import cp_model
import ortools
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..energy import calculate_energy
from ..models import (AcademicTerm, Equipment, Faculty, Room, Student,
                      TimetableSection, TimetableSession, TimetableSessionFaculty, TimetableSubject)
from ..timetable_import import detect_conflicts
from .validator import validate_assignment


def _is_lab(row: dict) -> bool:
    return "LAB" in ((row.get("subject_name") or "") + " " + row.get("raw_label", "")).upper()


def _session_data(db: Session, term: AcademicTerm) -> tuple[list[dict], list[dict], dict[str, int]]:
    rows = list(db.scalars(select(TimetableSession).where(TimetableSession.term_id == term.id)))
    sections = {row.id: row for row in db.scalars(select(TimetableSection).where(TimetableSection.term_id == term.id))}
    subject_by_id = {row.id: row.name for row in db.scalars(select(TimetableSubject).where(TimetableSubject.term_id == term.id))}
    rooms = list(db.scalars(select(Room).order_by(Room.number)))
    students = Counter(row.division_code for row in db.scalars(select(Student)))
    strengths = {}
    for section in sections.values():
        strengths[section.code] = students.get(section.division_code or section.code, 0)
    fac_links: dict[int, list[str]] = defaultdict(list)
    for session_id, initials in db.execute(
        select(TimetableSessionFaculty.session_id, Faculty.initials)
        .join(Faculty, Faculty.id == TimetableSessionFaculty.faculty_id)
        .join(TimetableSession, TimetableSession.id == TimetableSessionFaculty.session_id)
        .where(TimetableSession.term_id == term.id)
    ):
        fac_links[session_id].append(initials)
    output = []
    for row in rows:
        section = sections[row.section_id]
        output.append({"id": row.id, "term_code": term.code, "section_code": section.code,
            "day": row.day, "start_period": row.start_period, "end_period": row.end_period,
            "periods": list(range(row.start_period, row.end_period + 1)), "batch": row.batch,
            "block_id": row.block_id, "room_id": next((r.number for r in rooms if r.id == row.room_id), None),
            "room_db_id": row.room_id, "room_required": row.room_required, "room_inferred": row.room_inferred,
            "faculty_initials": fac_links.get(row.id, []), "raw_label": row.raw_label,
            "subject_name": subject_by_id.get(row.subject_id), "is_lab": _is_lab({"subject_name": subject_by_id.get(row.subject_id), "raw_label": row.raw_label}),
            "version": row.version, "section_strength": strengths[section.code],
            "section_strength_known": (section.division_code or section.code) in students})
    room_data = [{"room_id": r.number, "db_id": r.id, "floor": r.floor,
        "capacity": r.capacity,
        "capacity_effective": 0 if r.status in {"under_maintenance", "temporarily_unavailable"} else r.capacity,
        "status": r.status, "room_type": r.room_type, "timetable_eligible": r.timetable_eligible,
        "version": r.version,
        "connected_kw": sum(e.quantity * e.watts_each / 1000 for e in db.scalars(select(Equipment).where(Equipment.room_id == r.id)))} for r in rooms]
    return output, room_data, strengths


def _conflicts(sessions: list[dict]) -> tuple[list[dict], Counter]:
    conflicts = detect_conflicts(sessions)
    return conflicts, Counter(c["type"] for c in conflicts)


def solve_energy(db: Session, term: AcademicTerm, request, *, energy_weight: float = 1.0) -> dict:
    started = perf_counter()
    sessions, rooms, strengths = _session_data(db, term)
    forbidden_floors = set(request.forbid_floors)
    forbidden_rooms = set(request.forbid_rooms)
    closed_floors = set(getattr(request, "close_floors", []))
    closed_rooms = set(getattr(request, "close_rooms", []))
    blocked_floors = forbidden_floors | closed_floors
    blocked_rooms = forbidden_rooms | closed_rooms
    room_by_key = {r["room_id"]: r for r in rooms}
    selected_sections = set(request.sections)
    def selected(row: dict) -> bool:
        if not row["room_required"]:
            return False
        if request.movable == "all":
            return True
        if request.movable == "selected_sections":
            return row["section_code"] in selected_sections
        return row["room_inferred"]
    closure_sessions = {row["id"] for row in sessions if row["room_required"] and row["room_id"] and
                        (row["room_id"] in closed_rooms or room_by_key.get(row["room_id"], {}).get("floor") in closed_floors)}
    closure_active = bool(closed_floors or closed_rooms)
    if closure_active:
        # A closure scenario is an isolated what-if: sessions in affected
        # resources must leave, and every other session remains fixed.
        movable = {row["id"] for row in sessions if row["id"] in closure_sessions
                   and (not row["is_lab"] or not request.lock_labs)}
    else:
        movable = {row["id"] for row in sessions if selected(row) and (not row["is_lab"] or not request.lock_labs)}
    model = cp_model.CpModel()
    candidates: dict[tuple[int, str], cp_model.IntVar] = {}
    relocations: dict[int, cp_model.IntVar] = {}
    movable_by_id = {row["id"]: row for row in sessions if row["id"] in movable}
    slots_for_room: dict[tuple[str, str, int], list] = defaultdict(list)
    room_on: dict[tuple[str, str, int], cp_model.IntVar] = {}
    infeasible_reasons = []
    locked_closures = [row for row in sessions if row["id"] in closure_sessions and row["is_lab"] and request.lock_labs]
    if locked_closures:
        infeasible_reasons.append("closed room/floor contains locked lab sessions: " + ", ".join(str(row["id"]) for row in locked_closures))
        model.Add(0 == 1)
    for row in sessions:
        if row["id"] not in movable:
            continue
        compatible = []
        if not row["section_strength_known"]:
            infeasible_reasons.append(f"section strength is unavailable for section {row['section_code']}")
        for room in rooms:
            rtype = room["room_type"].lower()
            is_lab_room = "lab" in rtype or "computer" in rtype
            if not room["timetable_eligible"] or room["status"] != "available":
                continue
            if room["floor"] in blocked_floors or room["room_id"] in blocked_rooms:
                continue
            if row["is_lab"] and not is_lab_room:
                continue
            if not row["is_lab"] and not any(term in rtype for term in ("classroom", "seminar", "lab", "computer")):
                continue
            needed = row["section_strength"]
            if row["batch"] in {"B1", "B2"}:
                needed = (needed + 1) // 2
            if room["capacity_effective"] < needed:
                continue
            compatible.append(room)
        if not row["section_strength_known"]:
            compatible = []
        if not compatible:
            infeasible_reasons.append(f"session {row['id']} has no eligible room satisfying capacity, type, availability, and floor constraints")
        vars_for_session = []
        for room in compatible:
            var = model.NewBoolVar(f"assign_{row['id']}_{room['db_id']}")
            candidates[(row["id"], room["room_id"])] = var
            vars_for_session.append(var)
            for period in range(row["start_period"], row["end_period"] + 1):
                slots_for_room[(room["room_id"], row["day"], period)].append(var)
        model.AddExactlyOne(vars_for_session)
        changed = model.NewBoolVar(f"relocated_{row['id']}")
        relocations[row["id"]] = changed
        original = row["room_id"]
        orig_var = candidates.get((row["id"], original))
        if orig_var is not None:
            model.Add(changed + orig_var == 1)
        else:
            model.Add(changed == 1)
    if request.max_relocations is not None and relocations:
        model.Add(sum(relocations.values()) <= request.max_relocations)

    fixed_at: Counter = Counter()
    all_slot_keys = set(slots_for_room)
    for row in sessions:
        if not row["room_required"] or not row["room_id"]:
            continue
        if row["id"] in movable:
            continue
        for period in range(row["start_period"], row["end_period"] + 1):
            key = (row["room_id"], row["day"], period)
            fixed_at[key] += 1
            all_slot_keys.add(key)
    for key, vars_in_slot in slots_for_room.items():
        fixed_count = fixed_at[key]
        model.Add(sum(vars_in_slot) <= max(0, 1 - fixed_count))
    for row in sessions:
        if row["id"] not in movable or row["batch"] not in {"B1", "B2"} or not row["block_id"]:
            continue
        siblings = [s for s in sessions if s["block_id"] == row["block_id"] and s["day"] == row["day"]
                    and s["batch"] in {"B1", "B2"} and s["batch"] != row["batch"]]
        for sibling in siblings:
            for room in rooms:
                first = candidates.get((row["id"], room["room_id"]))
                second = candidates.get((sibling["id"], room["room_id"]))
                if first is not None and second is not None:
                    model.Add(first + second <= 1)
                elif first is not None and sibling["id"] not in movable and sibling["room_id"] == room["room_id"]:
                    model.Add(first == 0)

    room_ons = {}
    for room_id, day, period in sorted(all_slot_keys):
        on = model.NewBoolVar(f"room_on_{room_by_key[room_id]['db_id']}_{day}_{period}")
        room_ons[(room_id, day, period)] = on
        if fixed_at[(room_id, day, period)]:
            model.Add(on == 1)
        for var in slots_for_room.get((room_id, day, period), []):
            model.Add(var <= on)

    scale = 10000
    objective = []
    for (rid, _day, _period), on in room_ons.items():
        kw = room_by_key[rid]["connected_kw"]
        coefficient = round(energy_weight * kw * settings.period_hours * settings.energy_tariff_inr_per_kwh * scale)
        if coefficient:
            objective.append(coefficient * on)
    for sid, changed in relocations.items():
        if request.lambda_move:
            objective.append(round(request.lambda_move * scale) * changed)
        row = movable_by_id[sid]
        original = room_by_key.get(row["room_id"])
        for room in rooms:
            var = candidates.get((sid, room["room_id"]))
            if var is not None and original and request.lambda_floor:
                floors = abs(original["floor"] - room["floor"])
                people = row["section_strength"] // 2 if row["batch"] in {"B1", "B2"} else row["section_strength"]
                objective.append(round(request.lambda_floor * people * floors * scale) * var)
    model.Minimize(sum(objective) if objective else 0)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = request.time_limit_s
    solver.parameters.random_seed = request.seed
    solver.parameters.num_search_workers = 1
    status_code = solver.Solve(model)
    status_name = solver.StatusName(status_code)
    assignments = {row["id"]: row["room_id"] for row in sessions if row["room_required"]}
    changes = []
    if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for sid in movable:
            row = movable_by_id[sid]
            assigned_room = next(room_id for (session_id, room_id), var in candidates.items()
                                 if session_id == sid and solver.Value(var))
            assignments[sid] = assigned_room
            if assigned_room != row["room_id"]:
                old_room = room_by_key[row["room_id"]]
                new_room = room_by_key[assigned_room]
                changes.append({"session_id": sid, "from_room": row["room_id"], "to_room": assigned_room,
                    "expected_session_version": row["version"], "expected_from_room_version": old_room["version"],
                    "expected_to_room_version": new_room["version"], "section_code": row["section_code"],
                    "section_strength": row["section_strength"]})
    before_energy = calculate_energy(db, term)
    before, after = before_energy["timetable_occupancy"]["block"], before_energy["timetable_occupancy"]["block"]
    after_energy = before_energy
    if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        after_energy = calculate_energy(db, term, assignments={
            db_id: next(r["db_id"] for r in rooms if r["room_id"] == assigned)
            for db_id, assigned in assignments.items()})
        after = after_energy["timetable_occupancy"]["block"]
    before_conflicts, before_counts = _conflicts(sessions)
    after_sessions = [dict(row, room_id=assignments.get(row["id"], row["room_id"])) for row in sessions]
    after_conflicts, after_counts = _conflicts(after_sessions)
    unresolvable = [c for c in before_conflicts if not any(sessions[i]["id"] in movable for i in c["session_indices"])]
    # conflict detector indexes rows; expose stable session IDs instead.
    unresolvable_conflicts = [{"type": c["type"], "day": c["day"], "period": c["period"],
        "session_ids": [sessions[i]["id"] for i in c["session_indices"]]} for c in unresolvable]
    unique_affected_sections = sorted({change["section_code"] for change in changes})
    affected_students = sum(strengths.get(code, 0) for code in unique_affected_sections)
    solver_objective = solver.ObjectiveValue() / scale if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None
    validator = validate_assignment(sessions, rooms, assignments, movable_ids=movable,
        section_strengths=strengths, max_relocations=request.max_relocations,
        forbid_floors=blocked_floors, forbid_rooms=blocked_rooms, lock_labs=request.lock_labs)
    if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE) and not validator["valid"]:
        status_name = "MODEL_INVALID"
    return {"id": str(uuid.uuid4()), "status": "draft", "term_code": term.code,
        "solver_status": status_name, "solve_time_s": round(perf_counter() - started, 6),
        "ortools_version": ortools.__version__, "time_limit_s": request.time_limit_s,
        "seed": request.seed, "num_workers": 1, "objective_value": solver_objective,
        "objective": "minimize weekly room-on kWh × synthetic tariff + lambda_move × relocations + lambda_floor × students × floors changed",
        "before": {"kwh_week": before["kwh_week"], "cost_week_inr": before["cost_week_inr"], "clash_count": len(before_conflicts), "conflicts": dict(before_counts)},
        "after": {"kwh_week": after["kwh_week"], "cost_week_inr": after["cost_week_inr"], "clash_count": len(after_conflicts), "conflicts": dict(after_counts)},
        "relocations": len(changes), "affected_students": affected_students,
        "affected_sections": unique_affected_sections, "changes": changes,
        "unresolvable_source_clashes": unresolvable_conflicts, "validator": validator,
        "infeasible_reason": "; ".join(infeasible_reasons) if status_name == "INFEASIBLE" and infeasible_reasons else None,
        "data_status": "SYNTHETIC"}
