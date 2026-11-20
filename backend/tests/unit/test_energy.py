from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import EnergyBaseline, Equipment, Room
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
        assert by_number["A-F2-11"].provenance == "INFERRED"
        for row in baselines.values():
            assert row.daily_kwh == round(row.connected_load_kw * row.hours_per_day, 4)
            assert row.weekly_kwh == round(row.daily_kwh * row.days_per_week, 4)
            assert row.weekly_cost == round(row.weekly_kwh * row.tariff_per_kwh, 2)
        assert db.query(Equipment).count() == 129
        assert {room.building_id for room in rooms.values()} == {1}
