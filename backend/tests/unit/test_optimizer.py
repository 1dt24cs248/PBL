from contextlib import redirect_stdout
from io import StringIO

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import (AcademicTerm, Room, Student, TimetableSection,
                        TimetableSession)
from app.optimizer.service import solve_energy
from app.optimizer.validator import validate_assignment
from app.routers.optimizer import EnergyRequest
from app.seed import seed


def optimizer_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    with redirect_stdout(StringIO()):
        seed(db)
    term = db.scalar(select(AcademicTerm).where(AcademicTerm.code == "2026-27-ODD"))
    db.execute(delete(TimetableSession).where(TimetableSession.term_id == term.id))
    db.execute(delete(Student))
    for division, count in (("CSE-1", 55), ("CSE-2", 20)):
        for _ in range(count):
            db.add(Student(full_name="Synthetic optimizer test record", division_code=division,
                           provenance="SYNTHETIC"))
    section_rows = {row.code: row for row in db.scalars(select(TimetableSection).where(TimetableSection.term_id == term.id))}
    room_rows = {row.number: row for row in db.scalars(select(Room))}
    allowed = {"A-F1-01": 60, "A-F1-02": 30, "A-F1-03": 60}
    for room in room_rows.values():
        room.timetable_eligible = room.number in allowed
        room.status = "available"
        room.room_type = "classroom"
        if room.number in allowed:
            room.capacity = allowed[room.number]
    db.flush()
    db.add_all([
        TimetableSession(term_id=term.id, section_id=section_rows["C"].id, batch="ALL", day="Mon",
            start_period=1, end_period=1, room_id=room_rows["A-F1-03"].id,
            room_required=True, room_inferred=False, raw_label="synthetic fixed session"),
        TimetableSession(term_id=term.id, section_id=section_rows["A"].id, batch="ALL", day="Mon",
            start_period=1, end_period=1, room_id=room_rows["A-F1-02"].id,
            room_required=True, room_inferred=True, raw_label="synthetic movable session A"),
        TimetableSession(term_id=term.id, section_id=section_rows["B"].id, batch="ALL", day="Mon",
            start_period=1, end_period=1, room_id=room_rows["A-F1-01"].id,
            room_required=True, room_inferred=True, raw_label="synthetic movable session B"),
    ])
    db.commit()
    return engine, db, term, room_rows


def test_three_session_optimum_and_same_seed_are_exact():
    engine, db, term, room_rows = optimizer_db()
    try:
        sessions = list(db.scalars(select(TimetableSession).where(TimetableSession.term_id == term.id).order_by(TimetableSession.id)))
        original = {row.id: row.room_id for row in sessions}
        request = EnergyRequest(term=term.code, max_relocations=2, lambda_move=0, lambda_floor=0, seed=0)
        first = solve_energy(db, term, request)
        second = solve_energy(db, term, request)
        assert first["solver_status"] == "OPTIMAL"
        assert first["validator"]["valid"] is True
        expected = {"A-F1-01", "A-F1-02", "A-F1-03"}
        assigned = {change["session_id"]: change["to_room"] for change in first["changes"]}
        assert assigned == {sessions[1].id: "A-F1-01", sessions[2].id: "A-F1-02"}
        assert len(expected) == 3
        assert first["changes"] == second["changes"]
        assert first["objective_value"] == second["objective_value"]
        assert {row.id: row.room_id for row in db.scalars(select(TimetableSession).where(TimetableSession.term_id == term.id))} == original
        assert sessions[0].room_id == room_rows["A-F1-03"].id
    finally:
        db.close()
        engine.dispose()


def test_capacity_infeasible_and_max_relocations_do_not_write_sessions():
    engine, db, term, room_rows = optimizer_db()
    try:
        rows = list(db.scalars(select(TimetableSession).where(TimetableSession.term_id == term.id).order_by(TimetableSession.id)))
        original = {row.id: row.room_id for row in rows}
        room_rows["A-F1-01"].capacity = 10
        room_rows["A-F1-02"].capacity = 10
        db.commit()
        infeasible = solve_energy(db, term, EnergyRequest(term=term.code, lambda_move=0, lambda_floor=0))
        assert infeasible["solver_status"] == "INFEASIBLE"
        assert infeasible["changes"] == []
        assert {row.id: row.room_id for row in rows} == original
    finally:
        db.close()
        engine.dispose()


def test_forbidden_floor_and_relocation_limit_are_hard_constraints():
    engine, db, term, _rooms = optimizer_db()
    try:
        forbidden = solve_energy(db, term, EnergyRequest(term=term.code, forbid_floors=[1],
                                    max_relocations=2, lambda_move=0, lambda_floor=0))
        assert forbidden["solver_status"] == "INFEASIBLE"
        relocation_limited = solve_energy(db, term, EnergyRequest(term=term.code, max_relocations=0,
                                           lambda_move=0, lambda_floor=0))
        assert relocation_limited["solver_status"] == "INFEASIBLE"
    finally:
        db.close()
        engine.dispose()


def test_independent_validator_rejects_corrupted_assignments():
    rooms = [
        {"room_id": "R1", "floor": 1, "capacity": 20, "room_type": "classroom", "status": "available", "timetable_eligible": True},
        {"room_id": "R2", "floor": 2, "capacity": 80, "room_type": "classroom", "status": "available", "timetable_eligible": True},
    ]
    sessions = [
        {"id": 1, "day": "Mon", "start_period": 1, "end_period": 2, "section_code": "A", "batch": "ALL", "room_id": "R2", "room_required": True},
        {"id": 2, "day": "Mon", "start_period": 1, "end_period": 1, "section_code": "B", "batch": "ALL", "room_id": "R2", "room_required": True},
    ]
    result = validate_assignment(sessions, rooms, {1: "R1", 2: "R1"}, movable_ids={1, 2},
        section_strengths={"A": 50, "B": 10}, forbid_floors={1})
    kinds = {row["type"] for row in result["violations"]}
    assert {"capacity", "room_double_booking", "forbidden_room"}.issubset(kinds)
