import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import AcademicTerm, DivisionSectionMap, Faculty, Student, User
from app.security import hash_password
from app.seed import DEV_PASSWORD, seed


@pytest.fixture(scope="module")
def m2_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False)
    with SessionLocal() as db:
        seed(db)
        term = db.scalar(select(AcademicTerm).where(AcademicTerm.code == "2026-27-ODD"))
        faculty = db.scalar(select(Faculty).where(Faculty.term_id == term.id, Faculty.initials == "PP"))
        division = db.scalar(select(DivisionSectionMap).where(DivisionSectionMap.section_letter == "E"))
        student = db.scalar(select(Student).where(Student.division_code == division.division_code,
                                                  Student.lab_batch == "A1", Student.usn.is_not(None),
                                                  Student.usn.in_(select(User.username).where(User.role == "student"))))
        student_username = student.usn
        db.add(User(username="pp", full_name="Synthetic Faculty Test", password_hash=hash_password(DEV_PASSWORD),
                    role="teaching_faculty", department="CSE", provenance="SYNTHETIC"))
        db.commit()
        faculty_id = faculty.id

    def override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    client.faculty_id = faculty_id
    client.student_username = student_username
    yield client
    app.dependency_overrides.clear()
    engine.dispose()


def auth(client, username):
    result = client.post("/auth/login", json={"username": username, "password": DEV_PASSWORD})
    assert result.status_code == 200, result.text
    return {"Authorization": f"Bearer {result.json()['access_token']}"}


def test_student_identity_and_fifth_e_regression(m2_client):
    headers = auth(m2_client, m2_client.student_username)
    me = m2_client.get("/students/me", headers=headers)
    assert me.status_code == 200
    assert (me.json()["division_code"], me.json()["section_code"], me.json()["lab_batch"]) == ("CSE-5", "E", "A1")
    timetable = m2_client.get("/timetable/student/me", headers=headers)
    assert timetable.status_code == 200
    wednesday = [row for row in timetable.json()["sessions"] if row["day"] == "Wed"]
    indexed = {(row["periods"][0], row["subject_code"]): row for row in wednesday}
    assert indexed[(1, "BCS502")]["room_id"] == "A-F1-01"
    assert indexed[(1, "BCS502")]["faculty_name"] == "Mr. Parvathisha Pudugosula"
    assert indexed[(2, "BCS502")]["faculty_name"] == "Mr. Parvathisha Pudugosula"
    assert indexed[(5, "BCS515B")]["faculty_name"] == "Mrs Usha CR"
    assert indexed[(6, "BCS501")]["faculty_name"] == "Mrs. Manasa Sandeep"
    assert all(row["batch"] in {"ALL", "B1"} for row in timetable.json()["sessions"])


def test_sections_room_and_faculty_timetables(m2_client):
    student_headers = auth(m2_client, m2_client.student_username)
    own = m2_client.get("/sections/E/timetable?term=2026-27-ODD", headers=student_headers)
    assert own.status_code == 200
    other = m2_client.get("/sections/A/timetable?term=2026-27-ODD", headers=student_headers)
    assert other.status_code == 403
    rooms = m2_client.get("/rooms/A-108/timetable?term=2026-27-ODD", headers=student_headers)
    assert rooms.status_code == 200 and rooms.json()["room_id"] == "A-F1-10"
    faculty_headers = auth(m2_client, "pp")
    faculty = m2_client.get(
        f"/timetable/faculty/{m2_client.faculty_id}?term=2026-27-ODD", headers=faculty_headers
    )
    assert faculty.status_code == 200
    assert faculty.json()["initials"] == "PP"
    assert faculty.json()["sessions"]


def test_holiday_date_metadata_and_room_availability(m2_client):
    headers = auth(m2_client, "admin1")
    holiday = m2_client.get("/timetable/date/2026-11-10", headers=headers)
    assert holiday.status_code == 200
    assert holiday.json() == {"date": "2026-11-10", "weekday": "Tue", "holiday": "Deepavali 2026", "sessions": []}
    normal_day = m2_client.get("/timetable/date/2026-11-11", headers=headers)
    assert normal_day.status_code == 200 and normal_day.json()["weekday"] == "Wed"
    fifth_e = [row for row in normal_day.json()["sessions"] if row["section_code"] == "E"]
    by_period = {period: row for row in fifth_e for period in row["periods"]}
    assert by_period[1]["subject_code"] == by_period[2]["subject_code"] == "BCS502"
    assert by_period[1]["faculty_name"] == by_period[2]["faculty_name"] == "Mr. Parvathisha Pudugosula"
    assert by_period[5]["subject_code"] == "BCS515B"
    assert by_period[5]["faculty_name"] == "Mrs Usha CR"
    assert by_period[6]["subject_code"] == "BCS501"
    assert by_period[6]["faculty_name"] == "Mrs. Manasa Sandeep"
    availability = m2_client.get("/rooms/availability?day=Wed&period=1", headers=headers)
    assert availability.status_code == 200
    assert availability.json()["term_code"] == "2026-27-ODD"
    meta = m2_client.get("/meta/data-status", headers=headers)
    assert meta.status_code == 200 and meta.json()["counts"]["sessions"] == 475
    conflicts = m2_client.get("/timetable/conflicts?term=2026-27-ODD", headers=headers)
    assert conflicts.status_code == 200
    assert any(item["type"] == "room" for item in conflicts.json()["conflicts"])


def test_session_writes_are_admin_only_versioned_and_conflict_checked(m2_client):
    body = {"term_code": "2026-27-ODD", "section_code": "A", "batch": "ALL", "day": "Tue",
            "periods": [7], "subject_code": "BCS502", "room_id": "A-F4-03", "room_required": True,
            "raw_label": "manual test session", "block_id": "test-manual-block"}
    assert m2_client.post("/timetable/sessions", json=body,
                          headers=auth(m2_client, m2_client.student_username)).status_code == 403
    assert m2_client.post("/timetable/sessions", json=body,
                          headers=auth(m2_client, "hod_cse")).status_code == 403
    assert m2_client.post("/timetable/sessions", json=body,
                          headers=auth(m2_client, "fac1")).status_code == 403
    admin = auth(m2_client, "admin1")
    created = m2_client.post("/timetable/sessions", json=body, headers=admin)
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]
    assert created.json()["version"] == 1 and created.json()["provenance"] == "SYNTHETIC"
    conflicting = {**body, "section_code": "D", "raw_label": "conflicting test session"}
    rejected = m2_client.post("/timetable/sessions", json=conflicting, headers=admin)
    assert rejected.status_code == 409, rejected.text
    updated = m2_client.patch(f"/timetable/sessions/{session_id}",
                              json={"room_id": "A-F4-04", "expected_version": 1}, headers=admin)
    assert updated.status_code == 200 and updated.json()["version"] == 2
    stale = m2_client.patch(f"/timetable/sessions/{session_id}",
                            json={"room_id": "A-F4-03", "expected_version": 1}, headers=admin)
    assert stale.status_code == 409


def test_role_and_authentication_boundaries(m2_client):
    assert m2_client.get("/students/me").status_code == 401
    assert m2_client.get("/timetable/student/me").status_code == 401
    student = auth(m2_client, m2_client.student_username)
    assert m2_client.get("/admin/users", headers=student).status_code == 403
    maintenance = auth(m2_client, "maint1")
    assert m2_client.get("/students/me", headers=maintenance).status_code == 403
    assert m2_client.get("/timetable/student/me", headers=maintenance).status_code == 403
    assert m2_client.get("/sections/E/timetable?term=2026-27-ODD", headers=maintenance).status_code == 403
    hod = auth(m2_client, "hod_cse")
    assert m2_client.get("/timetable/conflicts?term=2026-27-ODD", headers=hod).status_code == 200
