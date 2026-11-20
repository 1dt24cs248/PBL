from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.dataset import parse_dataset
from app.models import DivisionSectionMap, Room, RoomAlias, Section, Student
from app.seed import seed


def test_dataset_parser_and_seed_counts(tmp_path):
    dataset = parse_dataset()
    assert len(dataset.rooms) == 66
    assert len(dataset.equipment) == 129
    assert len(dataset.aliases) == 5
    assert {room["building_id"] for room in dataset.rooms} == {"A"}
    engine = create_engine(f"sqlite:///{tmp_path / 'seed.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        report = seed(db, dataset)
        assert db.query(Room).count() == 66
        assert db.query(Student).filter(Student.usn.is_not(None)).count() == 342
        assert db.query(Student).filter(Student.usn.is_(None)).count() == 2
        assert db.query(Section).count() == 6
        assert db.query(DivisionSectionMap).count() == 344
        assert db.query(RoomAlias).count() == 5
        assert "A-F2-11" in report and "A-F2-12" in report
        # The seed is safe to rerun and keeps IDs / counts stable.
        seed(db, dataset)
        assert db.query(Room).count() == 66
        assert db.query(Student).count() == 344
        assert db.query(DivisionSectionMap).count() == 344


def test_roster_addendum_and_admission_numbers_are_not_usns():
    dataset = parse_dataset()
    by_usn = {student["usn"]: student for student in dataset.students if student["usn"]}
    assert {"1DT24CS198", "1DT24CS239", "1DT24CS272"}.issubset(by_usn)
    admission_rows = [student for student in dataset.students if student["usn"] is None]
    assert {student["source_identifier"] for student in admission_rows} == {
        "24UGDT1805-CS1", "24UGDT0186-CS1"
    }
    assert all(student["provenance"] == "REAL_DSATM_PDF" for student in dataset.students)
