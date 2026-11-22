from contextlib import redirect_stdout
from io import StringIO

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.energy import calculate_energy, calculate_utilization
from app.models import (AcademicTerm, EnergyBaseline, Equipment, Room, TimetableSection,
                        TimetableSession)
from app.seed import seed


def test_seeded_energy_baselines_match_synthetic_equipment(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'energy.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)
        rooms = {room.number: room for room in db.scalars(select(Room))}
        baselines = {row.room_id: row for row in db.scalars(select(EnergyBaseline))}
        by_number = {number: baselines[room.id] for number, room in rooms.items()}
        assert len(baselines) == 66
        assert by_number["A-G04"].connected_load_kw == 0.71
        assert rooms["A-G04"].estimated_connected_load_kw == 2.5
        assert by_number["A-F1-05"].connected_load_kw == 5.08
        assert by_number["A-G03"].connected_load_kw == 1.19
        assert by_number["A-B03"].connected_load_kw == 2.16
        assert by_number["A-F2-11"].connected_load_kw == 0
        assert by_number["A-F2-11"].provenance == "SYNTHETIC"
        assert rooms["A-F2-11"].capacity == 60
        assert rooms["A-F2-11"].room_type == "Classroom"
        assert rooms["A-F2-12"].capacity == 30
        assert rooms["A-F2-12"].room_type == "Computer Lab"
        assert rooms["A-F2-12"].provenance == "SYNTHETIC"
        for row in baselines.values():
            assert row.daily_kwh == round(row.connected_load_kw * row.hours_per_day, 4)
            assert row.weekly_kwh == round(row.daily_kwh * row.days_per_week, 4)
            assert row.weekly_cost == round(row.weekly_kwh * row.tariff_per_kwh, 2)
        assert db.query(Equipment).count() == 129
        assert {room.building_id for room in rooms.values()} == {1}


@pytest.fixture
def energy_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    with redirect_stdout(StringIO()):
        seed(db)
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _clear_active_sessions(db):
    term = db.scalar(select(AcademicTerm).where(AcademicTerm.code == "2026-27-ODD"))
    db.execute(delete(TimetableSession).where(TimetableSession.term_id == term.id))
    db.flush()
    section = db.scalar(select(TimetableSection).where(TimetableSection.term_id == term.id,
                                                       TimetableSection.code == "A"))
    return term, section


def test_hand_calculated_classroom_lab_and_seminar_energy(energy_db):
    db = energy_db
    term, section = _clear_active_sessions(db)
    rooms = {row.number: row for row in db.scalars(select(Room))}
    for number in ("A-F1-01", "A-F1-05", "A-G03"):
        db.add(TimetableSession(term_id=term.id, section_id=section.id, batch="ALL", day="Mon",
            start_period=1, end_period=1, room_id=rooms[number].id, room_required=True,
            raw_label="synthetic energy test", room_inferred=False))
    db.commit()
    result = calculate_energy(db, term)
    by_room = {row["room_id"]: row for row in result["timetable_occupancy"]["rooms"]}
    period_hours = 55 / 60
    for number, kw in (("A-F1-01", 0.71), ("A-F1-05", 5.08), ("A-G03", 1.19)):
        row = by_room[number]
        assert row["connected_kw"] == pytest.approx(kw)
        assert row["occupied_periods_week"] == 1
        assert row["kwh_week"] == pytest.approx(kw * period_hours)
        assert row["cost_week_inr"] == pytest.approx(kw * period_hours * 8.5, abs=0.01)


def test_energy_baseline_sums_rooms_and_floors(energy_db):
    db = energy_db
    term, section = _clear_active_sessions(db)
    room = db.scalar(select(Room).where(Room.number == "A-F2-02"))
    db.add(TimetableSession(term_id=term.id, section_id=section.id, batch="ALL", day="Mon",
        start_period=1, end_period=2, room_id=room.id, room_required=True,
        raw_label="synthetic energy test", room_inferred=False))
    db.commit()
    result = calculate_energy(db, term)
    occupancy = result["timetable_occupancy"]
    assert occupancy["block"]["kwh_week"] == pytest.approx(sum(row["kwh_week"] for row in occupancy["rooms"]))
    assert occupancy["block"]["cost_week_inr"] == pytest.approx(sum(row["cost_week_inr"] for row in occupancy["floors"]))
    flat = result["flat_spec_baseline_6h_x_5days"]
    assert flat["block"]["kwh_week"] == pytest.approx(sum(row["kwh_week"] for row in flat["rooms"]))


def test_utilization_uses_half_batch_strength_and_six_days(energy_db):
    db = energy_db
    term, section = _clear_active_sessions(db)
    room = db.scalar(select(Room).where(Room.number == "A-F1-02"))
    db.add(TimetableSession(term_id=term.id, section_id=section.id, batch="B1", day="Mon",
        start_period=1, end_period=2, room_id=room.id, room_required=True,
        raw_label="synthetic batch utilization test", room_inferred=False))
    db.commit()
    result = calculate_utilization(db, term)
    row = next(item for item in result["rooms"] if item["room_id"] == room.number)
    assert row["occupied_periods_week"] == 2
    assert row["available_periods_week"] == result["periods_per_day"] * 6
    assert row["seat_utilization"] == pytest.approx(29 / room.capacity, abs=0.0001)
    assert row["room_id"] not in result["rooms_never_used"]
