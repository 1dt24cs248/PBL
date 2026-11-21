"""Independent hard-constraint validator for proposed room assignments."""
from collections import defaultdict


def _slot_keys(session: dict):
    start = session.get("start_period", min(session.get("periods", [1])))
    end = session.get("end_period", max(session.get("periods", [start])))
    return [(session["day"], p) for p in range(start, end + 1)]


def _lab(session: dict) -> bool:
    return bool(session.get("is_lab") or "LAB" in (session.get("subject_name") or "").upper()
                or "LAB" in session.get("raw_label", "").upper())


def validate_assignment(sessions: list[dict], rooms: list[dict], assignments: dict[int, str], *,
                        movable_ids: set[int] | None = None, section_strengths: dict[str, int] | None = None,
                        max_relocations: int | None = None, forbid_floors: set[int] | None = None,
                        forbid_rooms: set[str] | None = None, lock_labs: bool = True) -> dict:
    movable_ids = movable_ids or set()
    section_strengths = section_strengths or {}
    forbid_floors, forbid_rooms = forbid_floors or set(), forbid_rooms or set()
    room_by_id = {room["room_id"]: room for room in rooms}
    chosen = {session["id"]: assignments.get(session["id"], session.get("room_id")) for session in sessions}
    violations = []
    for session in sessions:
        sid, rid = session["id"], chosen[session["id"]]
        if not session.get("room_required", True):
            if rid is not None:
                violations.append({"type": "roomless_assignment", "session_id": sid})
            continue
        if rid is None or rid not in room_by_id:
            violations.append({"type": "missing_or_unknown_room", "session_id": sid, "room_id": rid})
            continue
        room = room_by_id[rid]
        # Hard room constraints apply to optimizer-created assignments. Fixed
        # source rows may already violate the modeled inventory; preserve and
        # report those as source conditions instead of making drafts impossible.
        if sid in movable_ids:
            if room.get("status", "available") != "available":
                violations.append({"type": "room_unavailable", "session_id": sid, "room_id": rid})
            if room.get("timetable_eligible", True) is False:
                violations.append({"type": "room_not_eligible", "session_id": sid, "room_id": rid})
            if rid in forbid_rooms or room.get("floor") in forbid_floors:
                violations.append({"type": "forbidden_room", "session_id": sid, "room_id": rid})
            room_type = str(room.get("room_type", "")).lower()
            if _lab(session) and "lab" not in room_type and "computer" not in room_type:
                violations.append({"type": "room_type", "session_id": sid, "room_id": rid})
            if not _lab(session) and not any(word in room_type for word in ("classroom", "seminar", "lab", "computer")):
                violations.append({"type": "room_type", "session_id": sid, "room_id": rid})
            section_size = section_strengths.get(session.get("section_code"), session.get("section_strength", 0))
            if session.get("batch") in {"B1", "B2"}:
                section_size = (section_size + 1) // 2
            capacity = room.get("capacity_effective", room.get("capacity", 0))
            if capacity < section_size:
                violations.append({"type": "capacity", "session_id": sid, "room_id": rid,
                                   "required": section_size, "capacity": capacity})
        if sid not in movable_ids and assignments.get(sid, rid) != session.get("room_id"):
            violations.append({"type": "fixed_session_changed", "session_id": sid})
        if lock_labs and _lab(session) and sid in movable_ids:
            violations.append({"type": "locked_lab_moved", "session_id": sid})

    slots = defaultdict(list)
    for session in sessions:
        if session.get("room_required") and chosen.get(session["id"]):
            for day, period in _slot_keys(session):
                slots[(chosen[session["id"]], day, period)].append(session["id"])
    for (rid, day, period), ids in slots.items():
        if len(ids) > 1 and any(identifier in movable_ids for identifier in ids):
            violations.append({"type": "room_double_booking", "room_id": rid, "day": day,
                               "period": period, "session_ids": sorted(ids)})
    parallel = defaultdict(dict)
    for session in sessions:
        if session.get("batch") in {"B1", "B2"} and session.get("block_id"):
            parallel[(session["block_id"], session.get("day"))][session["batch"]] = chosen[session["id"]]
    for key, batch_rooms in parallel.items():
        if "B1" in batch_rooms and "B2" in batch_rooms and batch_rooms["B1"] == batch_rooms["B2"]:
            violations.append({"type": "parallel_batches_same_room", "block_id": key[0]})
    relocations = sum(chosen[s["id"]] != s.get("room_id") for s in sessions if s["id"] in movable_ids)
    if max_relocations is not None and relocations > max_relocations:
        violations.append({"type": "max_relocations", "limit": max_relocations, "actual": relocations})
    return {"valid": not violations, "violations": violations}
