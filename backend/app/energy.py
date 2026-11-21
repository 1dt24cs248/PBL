"""Deterministic room energy and utilization calculations."""
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .models import (AcademicTerm, Equipment, Room, Student, TimetableSection,
                    TimetableSession)


def connected_loads(db: Session, rooms: list[Room]) -> dict[int, float]:
    totals = {room.id: 0.0 for room in rooms}
    for equipment in db.scalars(select(Equipment).where(Equipment.room_id.in_(totals))):
        totals[equipment.room_id] += equipment.quantity * equipment.watts_each / 1000
    return totals


def term_sessions(db: Session, term: AcademicTerm) -> list[TimetableSession]:
    return list(db.scalars(select(TimetableSession).where(TimetableSession.term_id == term.id)))


def calculate_energy(db: Session, term: AcademicTerm, *, assignments: dict[int, int] | None = None) -> dict:
    rooms = list(db.scalars(select(Room).order_by(Room.floor, Room.number)))
    loads = connected_loads(db, rooms)
    sessions = term_sessions(db, term)
    occupancy: dict[int, set[tuple[str, int]]] = defaultdict(set)
    occupancy_counts: dict[tuple[int, str, int], int] = defaultdict(int)
    room_ids = {room.id for room in rooms}
    for row in sessions:
        rid = (assignments or {}).get(row.id, row.room_id)
        if row.room_required and rid in room_ids:
            for period in range(row.start_period, row.end_period + 1):
                occupancy[rid].add((row.day, period))
                occupancy_counts[(rid, row.day, period)] += 1

    room_values = []
    clashes = 0
    flat_rooms = []
    for room in rooms:
        occupied = len(occupancy[room.id])
        connected_kw = loads[room.id]
        weekly_slots = settings.periods_per_day * 6
        kwh = (occupied + (weekly_slots - occupied) * settings.standby_fraction) * settings.period_hours * connected_kw
        cost = kwh * settings.energy_tariff_inr_per_kwh
        room_values.append({"room_id": room.number, "floor": room.floor, "connected_kw": round(connected_kw, 6),
                            "occupied_periods_week": occupied, "kwh_week": round(kwh, 6),
                            "cost_week_inr": round(cost, 2), "data_status": "SYNTHETIC"})
        clashes += sum(value > 1 for (rid, _day, _period), value in occupancy_counts.items() if rid == room.id)
        flat_kwh = connected_kw * 6 * 5
        flat_rooms.append({"room_id": room.number, "kwh_week": round(flat_kwh, 6),
                           "cost_week_inr": round(flat_kwh * settings.energy_tariff_inr_per_kwh, 2)})
    floors, flat_floor_rows = [], []
    for floor in sorted({room.floor for room in rooms}):
        members = [row for row in room_values if row["floor"] == floor]
        flat_members = [row for row in flat_rooms if next(room.floor for room in rooms if room.number == row["room_id"]) == floor]
        floors.append({"floor": floor, "occupied_periods_week": sum(row["occupied_periods_week"] for row in members),
                       "kwh_week": round(sum(row["kwh_week"] for row in members), 6),
                       "cost_week_inr": round(sum(row["cost_week_inr"] for row in members), 2)})
        flat_floor_rows.append({"floor": floor, "kwh_week": round(sum(row["kwh_week"] for row in flat_members), 6),
                                "cost_week_inr": round(sum(row["cost_week_inr"] for row in flat_members), 2)})
    return {"term_code": term.code, "period_hours": settings.period_hours,
            "tariff_inr_per_kwh": settings.energy_tariff_inr_per_kwh, "data_status": "SYNTHETIC",
            "timetable_occupancy": {"rooms": room_values, "floors": floors,
                "block": {"occupied_periods_week": sum(row["occupied_periods_week"] for row in room_values),
                          "kwh_week": round(sum(row["kwh_week"] for row in room_values), 6),
                          "cost_week_inr": round(sum(row["cost_week_inr"] for row in room_values), 2)},
                "recorded_room_clashes": clashes},
            "flat_spec_baseline_6h_x_5days": {"rooms": flat_rooms, "floors": flat_floor_rows,
                "block": {"kwh_week": round(sum(row["kwh_week"] for row in flat_rooms), 6),
                          "cost_week_inr": round(sum(row["cost_week_inr"] for row in flat_rooms), 2)},
                "label": "Fixed equipment load × 6 h/day × 5 days/week"}}


def calculate_utilization(db: Session, term: AcademicTerm) -> dict:
    rooms = list(db.scalars(select(Room).order_by(Room.floor, Room.number)))
    sessions = term_sessions(db, term)
    sections = {row.id: row for row in db.scalars(select(TimetableSection))}
    student_counts = dict(db.execute(select(Student.division_code, func.count(Student.id))
                                     .group_by(Student.division_code)).all())
    slots: dict[int, set[tuple[str, int]]] = defaultdict(set)
    seat_max: dict[int, float] = {}
    for session in sessions:
        if not session.room_required or session.room_id is None:
            continue
        for period in range(session.start_period, session.end_period + 1):
            slots[session.room_id].add((session.day, period))
        section = sections[session.section_id]
        division = section.division_code or section.code
        strength = student_counts.get(division, 0)
        if session.batch in {"B1", "B2"}:
            strength = strength / 2
        room = next((room for room in rooms if room.id == session.room_id), None)
        if room:
            effective_capacity = 0 if room.status in {"under_maintenance", "temporarily_unavailable"} else room.capacity
        else:
            effective_capacity = 0
        if effective_capacity:
            seat_max[session.room_id] = max(seat_max.get(session.room_id, 0), strength / effective_capacity)
    rows, never_used, under_half = [], [], []
    total_periods = settings.periods_per_day * 6
    for room in rooms:
        occupied = len(slots[room.id])
        capacity = 0 if room.status in {"under_maintenance", "temporarily_unavailable"} else room.capacity
        ratio = seat_max.get(room.id)
        row = {"room_id": room.number, "occupied_periods_week": occupied,
               "available_periods_week": total_periods,
               "occupancy_percent": round(100 * occupied / total_periods, 2),
               "capacity_effective": capacity, "seat_utilization": round(ratio, 4) if ratio is not None else None,
               "data_status": "INFERRED" if ratio is not None else "SYNTHETIC"}
        rows.append(row)
        if not occupied:
            never_used.append(room.number)
        elif ratio is not None and ratio < 0.5:
            under_half.append({"room_id": room.number, "seat_utilization": round(ratio, 4)})
    return {"term_code": term.code, "periods_per_day": settings.periods_per_day, "days_per_week": 6,
            "data_status": "INFERRED", "rooms": rows, "rooms_never_used": never_used,
            "rooms_under_50_percent_seat_utilization": under_half}
