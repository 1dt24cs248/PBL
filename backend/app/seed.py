"""Idempotent M1 seed loaded from docs/dataset_spec.md."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import SessionLocal
from .config import settings
from .dataset import Dataset, parse_dataset
from .models import (Building, DivisionSectionMap, EnergyBaseline, Equipment, Holiday,
                     NavEdge, NavNode, Room, RoomAlias, Section, Student, User)
from .security import hash_password

DEV_PASSWORD = "Pass@123"  # synthetic dev password only
USERS = [
    ("admin1", "Synthetic Admin", "admin", None),
    ("maint1", "Synthetic Maintenance", "maintenance", None),
    ("hod_cse", "Synthetic HOD CSE", "hod", "CSE"),
    ("fac1", "Synthetic Faculty 1", "teaching_faculty", "CSE"),
    ("stu1", "Synthetic Student 1", "student", "CSE"),
]


def seed(db: Session, dataset: Dataset | None = None) -> str:
    data = dataset or parse_dataset()
    for username, name, role, dept in USERS:
        if db.scalar(select(User).where(User.username == username)) is None:
            db.add(User(username=username, full_name=name, role=role, department=dept,
                        password_hash=hash_password(DEV_PASSWORD), provenance="SYNTHETIC"))
    building = db.scalar(select(Building).where(Building.code == "A"))
    if building is None:
        building = Building(code="A", name="A Block", floors=7, provenance="SYNTHETIC")
        db.add(building)
        db.flush()
    room_rows = {}
    for row in data.rooms:
        room = db.scalar(select(Room).where(Room.building_id == building.id, Room.number == row["room_id"]))
        if room is None:
            room = Room(building_id=building.id, number=row["room_id"], floor=row["floor_number"],
                        capacity=row["capacity_students"], room_type=row["facility_type"],
                        facilities="", status="available", version=1, name=row["room_name"],
                        department=row["department"], estimated_connected_load_kw=row["estimated_connected_load_kw"],
                        timetable_eligible=row["timetable_eligible"], provenance=row["provenance"], notes=row["notes"])
        else:
            for attr, value in (("floor", row["floor_number"]), ("capacity", row["capacity_students"]),
                                ("room_type", row["facility_type"]), ("name", row["room_name"]),
                                ("department", row["department"]),
                                ("estimated_connected_load_kw", row["estimated_connected_load_kw"]),
                                ("timetable_eligible", row["timetable_eligible"]),
                                ("provenance", row["provenance"]), ("notes", row["notes"])):
                setattr(room, attr, value)
        db.add(room)
        db.flush()
        room_rows[row["room_id"]] = room
    for room_id, alias, provenance in data.aliases:
        alias_row = db.scalar(select(RoomAlias).where(RoomAlias.alias == alias))
        if alias_row is None:
            db.add(RoomAlias(room_id=room_rows[room_id].id, alias=alias, provenance=provenance))
        else:
            alias_row.room_id = room_rows[room_id].id
            alias_row.provenance = provenance
    for idx, row in enumerate(data.equipment, 1):
        code = f"EQ{idx:04d}"
        if db.scalar(select(Equipment).where(Equipment.equipment_code == code)) is None:
            db.add(Equipment(equipment_code=code, room_id=room_rows[row["room_id"]].id,
                             name=row["name"], quantity=row["quantity"], watts_each=row["watts_each"],
                             provenance=row["provenance"]))
    for row in data.rooms:
        if db.scalar(select(EnergyBaseline).where(EnergyBaseline.baseline_code == row["energy_baseline_code"])) is None:
            kw = row["energy_connected_load_kw"]
            daily = round(kw * 6, 4)
            weekly = round(daily * 5, 4)
            db.add(EnergyBaseline(baseline_code=row["energy_baseline_code"], room_id=room_rows[row["room_id"]].id,
                                  connected_load_kw=kw, hours_per_day=6, days_per_week=5, tariff_per_kwh=8.5,
                                  daily_kwh=daily, weekly_kwh=weekly, weekly_cost=round(weekly * 8.5, 2),
                                  provenance="INFERRED" if row["provenance"] == "INFERRED" else "SYNTHETIC"))
    section_rows = {}
    for row in data.sections:
        section = db.scalar(select(Section).where(Section.code == row["code"]))
        if section is None:
            section = Section(code=row["code"], name=row["name"], home_room_id=room_rows[row["home_room_id"]].id,
                              declared_student_count=row["declared_student_count"], provenance=row["provenance"])
            db.add(section)
        section_rows[row["code"]] = section
    db.flush()
    for row in data.students:
        student = db.scalar(select(Student).where(Student.usn == row["usn"])) if row["usn"] else None
        if row["usn"] is None:
            student = db.scalar(select(Student).where(Student.source_identifier == row["source_identifier"]))
        if student is None:
            student = Student(usn=row["usn"], source_identifier=row["source_identifier"],
                              full_name=row["full_name"], gender=row["gender"], lab_batch=row["lab_batch"],
                              division_code=row["section_code"],
                              provenance=row["provenance"])
            db.add(student)
            db.flush()
        student.division_code = row["section_code"]
    for number in range(1, 7):
        division = f"CSE-{number}"
        mapping = db.scalar(select(DivisionSectionMap).where(DivisionSectionMap.division_code == division))
        if mapping is None:
            mapping = DivisionSectionMap(division_code=division, section_letter=chr(ord("A") + number - 1),
                                         data_status="INFERRED", admin_editable=True, provenance="INFERRED")
            db.add(mapping)
        else:
            mapping.section_letter = chr(ord("A") + number - 1)
            mapping.data_status = "INFERRED"
            mapping.admin_editable = True
            mapping.provenance = "INFERRED"
    students_by_usn = {student.usn: student for student in db.scalars(select(Student).where(Student.usn.is_not(None)))}
    configured_demo_usns = [value.strip() for value in settings.demo_student_usns.split(",") if value.strip()]
    if not configured_demo_usns:
        known_usns = sorted(value for value in students_by_usn if value)
        # Preserve the prior five-account development selection without
        # checking personal identifiers into source control.
        configured_demo_usns = known_usns[:4] + known_usns[247:248]
    for usn in configured_demo_usns:
        student = students_by_usn.get(usn)
        if student is None:
            raise ValueError(f"Configured demo student USN is absent from dataset: {usn}")
        if db.scalar(select(User).where(User.username == usn)) is None:
            db.add(User(username=usn, full_name=student.full_name, role="student", department="CSE",
                        password_hash=hash_password(DEV_PASSWORD), provenance="SYNTHETIC"))
    for row in data.holidays:
        holiday_date = date.fromisoformat(row["holiday_date"])
        if db.scalar(select(Holiday).where(Holiday.holiday_date == holiday_date)) is None:
            db.add(Holiday(holiday_date=holiday_date, name=row["name"], provenance=row["provenance"]))
    _seed_floorplan(db, room_rows)
    db.commit()
    report = _count_report(db, data)
    (Path(__file__).resolve().parents[2] / "docs" / "DATA_ISSUES.md").write_text(report, encoding="utf-8")
    print(report)
    from .timetable_import import import_timetables
    import_timetables(db)
    return report


def _seed_floorplan(db: Session, room_rows: dict[str, Room]) -> None:
    """Keep a new empty database aligned with the JSON-backed Alembic seed."""
    import json

    artifact_path = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "floorplan.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    node_rows: dict[str, NavNode] = {}
    for floor in artifact["floors"]:
        for row in floor["rooms"]:
            room = room_rows[row["room_id"]]
            geometry = row["geometry"]
            room.x, room.y, room.w, room.h = geometry["x"], geometry["y"], geometry["w"], geometry["h"]
        for row in floor["nodes"]:
            node = db.scalar(select(NavNode).where(NavNode.node_key == row["node_key"]))
            if node is None:
                node = NavNode(**{key: row[key] for key in (
                    "node_key", "floor", "node_type", "x", "y", "room_id", "provenance"
                )})
                db.add(node)
            else:
                for name in ("floor", "node_type", "x", "y", "room_id", "provenance"):
                    setattr(node, name, row[name])
            node_rows[row["node_key"]] = node
    db.flush()
    for row in artifact["edges"]:
        from_node, to_node = node_rows[row["from"]], node_rows[row["to"]]
        edge = db.scalar(select(NavEdge).where(
            NavEdge.from_node_id == from_node.id,
            NavEdge.to_node_id == to_node.id,
            NavEdge.mode == row["mode"],
        ))
        values = {
            "distance_m": row["distance_m"], "floor_delta": row["floor_delta"],
            "wait_seconds": row["wait_seconds"], "bidirectional": row["bidirectional"],
            "provenance": row["provenance"],
        }
        if edge is None:
            db.add(NavEdge(from_node_id=from_node.id, to_node_id=to_node.id,
                           mode=row["mode"], **values))
        else:
            for name, value in values.items():
                setattr(edge, name, value)


def _count_report(db: Session, data: Dataset) -> str:
    students = list(db.scalars(select(Student)))
    division_counts = dict(db.execute(
        select(Student.division_code, func.count(Student.id))
        .group_by(Student.division_code)
    ).all())
    usns = sum(student.usn is not None for student in students)
    no_usn = sum(student.usn is None for student in students)
    return "\n".join([
        "# M1 Dataset Seed Report",
        "",
        "Counts after idempotent seed (A-Block only):",
        f"- Rooms: {db.query(Room).count()} (64 parsed CSV rows + 2 M1 additions)",
        f"- Official USNs: {usns}",
        f"- Students without USN: {no_usn}",
        "- Students per division: " + ", ".join(f"{key}: {division_counts[key]}" for key in sorted(division_counts)),
        f"- Equipment rows: {db.query(Equipment).count()}",
        f"- Energy baselines: {db.query(EnergyBaseline).count()}",
        f"- Room aliases: {db.query(RoomAlias).count()}",
        f"- Sections: {db.query(Section).count()}",
        f"- Division-section mappings: {db.query(DivisionSectionMap).count()}",
        f"- Holidays: {db.query(Holiday).count()}",
        "",
        "## INFERRED decisions",
        *[f"- {item}" for item in data.inferred],
        "",
        "## Provenance",
        "Student roster and division assignments are REAL_DSATM_PDF. Room infrastructure, equipment and energy calculations are SYNTHETIC per the spec. Additional room fields, missing source attributes, and the Deepavali entry supplied by M1 are tagged INFERRED.",
        "",
        "M1 roster, room and energy seed report. M2 timetable import results are appended below.",
        "",
    ])


if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session)
