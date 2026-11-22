import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import AcademicTerm, DivisionSectionMap, Faculty, Student, TimetableSession, User
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
    client.SessionLocal = SessionLocal
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


def test_m7_room_capacity_and_availability_filters(m2_client):
    headers = auth(m2_client, "admin1")
    rooms_response = m2_client.get("/rooms", headers=headers)
    assert rooms_response.status_code == 200
    rooms = rooms_response.json()
    assert len(rooms) == 66
    assert all("timetable_eligible" in row for row in rooms)
    added = {row["number"]: row for row in rooms if row["number"] in {"A-F2-11", "A-F2-12"}}
    assert added["A-F2-11"]["capacity"] == 60
    assert added["A-F2-11"]["room_type"] == "Classroom"
    assert added["A-F2-11"]["data_status"] == "SYNTHETIC"
    assert added["A-F2-12"]["capacity"] == 30
    assert added["A-F2-12"]["room_type"] == "Computer Lab"
    assert added["A-F2-12"]["data_status"] == "SYNTHETIC"
    default = m2_client.get("/rooms/availability?day=Wed&period=1", headers=headers).json()
    all_rooms = m2_client.get(
        "/rooms/availability?day=Wed&period=1&include_non_timetable=true", headers=headers
    ).json()
    assert len(default["rooms"]) == sum(row["timetable_eligible"] for row in rooms) == 32
    assert len(all_rooms["rooms"]) == 66
    assert default["term_code"] == all_rooms["term_code"] == "2026-27-ODD"


def test_m7_timetable_fields_period_grid_and_calendar(m2_client):
    headers = auth(m2_client, m2_client.student_username)
    timetable = m2_client.get("/timetable/student/me", headers=headers).json()
    required = {"subject_code", "subject_name", "session_type", "start_time", "end_time",
                "faculty_names", "faculty_details", "room_id", "room_real_label", "room_inferred",
                "batch", "block_id", "room_required", "provenance"}
    assert timetable["sessions"]
    assert all(required.issubset(session) for session in timetable["sessions"])
    assert all(isinstance(session["faculty_names"], list) for session in timetable["sessions"])
    assert all(session["session_type"] in {"Lecture", "Lab", "Activity"} for session in timetable["sessions"])
    assert all(isinstance(session["start_time"], str) and isinstance(session["end_time"], str)
               for session in timetable["sessions"])
    assert any(session["session_type"] == "Activity" and not session["room_required"]
               for session in timetable["sessions"])

    periods = m2_client.get("/meta/periods", headers=headers).json()
    assert periods["periods"] == [
        {"period": 1, "start": "09:30", "end": "10:25"},
        {"period": 2, "start": "10:25", "end": "11:20"},
        {"period": 3, "start": "11:35", "end": "12:30"},
        {"period": 4, "start": "12:30", "end": "13:25"},
        {"period": 5, "start": "14:15", "end": "15:10"},
        {"period": 6, "start": "15:10", "end": "16:05"},
        {"period": 7, "start": "16:05", "end": "17:00"},
    ]
    assert periods["breaks"] == [
        {"after_period": 2, "label": "Tea", "start": "11:20", "end": "11:35"},
        {"after_period": 4, "label": "Lunch", "start": "13:25", "end": "14:15"},
    ]

    for day, name in (("2026-11-10", "Deepavali 2026"), ("2026-11-27", "Kanaka Jayanthi")):
        result = m2_client.get(f"/timetable/date/{day}", headers=headers).json()
        assert result["holiday"] == name and result["sessions"] == []
    holidays = m2_client.get("/calendar/holidays", headers=headers).json()
    assert [(row["date"], row["name"], row["source"]) for row in holidays] == [
        ("2026-11-10", "Deepavali 2026", "M1"),
        ("2026-11-27", "Kanaka Jayanthi", "ERP_SCREENSHOT"),
    ]
    calendar = m2_client.get("/calendar/summary", headers=headers).json()
    assert calendar["holidays"] == holidays
    assert all(term["start_date"] is None and term["end_date"] is None for term in calendar["terms"])
    assert "not known" in calendar["note"]


def test_m7_erp_demo_endpoints_are_synthetic_deterministic_and_student_only(m2_client, monkeypatch):
    from datetime import date
    from app.routers import student_demo

    monkeypatch.setattr(student_demo, "_today", lambda: date(2026, 11, 21))
    endpoints = ("/students/me/profile", "/students/me/attendance?from=2026-10-01&to=2026-11-30",
                 "/students/me/attendance/summary", "/students/me/lms/subjects", "/students/me/fees")
    assert all(m2_client.get(path).status_code == 401 for path in endpoints)
    student_headers = auth(m2_client, m2_client.student_username)
    with m2_client.SessionLocal() as db:
        session_count_before_demo = db.scalar(select(func.count()).select_from(TimetableSession))
    responses = [m2_client.get(path, headers=student_headers) for path in endpoints]
    assert all(response.status_code == 200 for response in responses)
    assert all(response.json()["data_status"] == "SYNTHETIC" for response in responses)
    profile = responses[0].json()
    assert profile["section_label"] == "CS-5-E"
    assert profile["section_mapping_status"] == "INFERRED"
    assert profile["roll_no"] is None and profile["home_room"]["code"] == "A-F5-02"
    assert not {"phone", "email", "parent", "photo"} & set(profile)
    ignored_identifier = m2_client.get(
        f"/students/me/profile?usn={m2_client.student_username}", headers=student_headers
    ).json()
    if ignored_identifier["usn"] != profile["usn"]:
        pytest.fail("Profile must derive identity from the authenticated token")
    with m2_client.SessionLocal() as db:
        other_username = db.scalar(select(User.username).where(
            User.role == "student", User.username != m2_client.student_username
        ).order_by(User.username))
    if other_username:
        other_profile = m2_client.get(
            "/students/me/profile", headers=auth(m2_client, other_username)
        ).json()
        if other_profile["usn"] != other_username:
            pytest.fail("A second student token must return only its own profile")

    grid = responses[1].json()["days"]
    assert m2_client.get(endpoints[1], headers=student_headers).json()["days"] == grid
    assert grid == sorted(grid, key=lambda row: row["date"], reverse=True)
    assert all(date.fromisoformat(row["date"]) < date(2026, 11, 21) for row in grid)
    assert all(row["weekday"] != "Sun" for row in grid)
    assert any(row["date"] == "2026-11-10" and row["slots"][0]["status"] == "-" for row in grid)
    monkeypatch.setattr(student_demo, "_today", lambda: date(2026, 12, 1))
    second_holiday = m2_client.get(
        "/students/me/attendance?from=2026-11-27&to=2026-11-27", headers=student_headers
    ).json()["days"]
    assert second_holiday[0]["slots"][0]["status"] == "-"
    monkeypatch.setattr(student_demo, "_today", lambda: date(2026, 11, 21))
    future = m2_client.get("/students/me/attendance?from=2026-11-22&to=2026-12-01",
                           headers=student_headers).json()["days"]
    assert future == []
    summary = responses[2].json()
    generated = m2_client.get("/students/me/attendance", headers=student_headers).json()["days"]
    values = [slot["status"] for day in generated for slot in day["slots"] if slot["status"] in {"P", "A", "NA"}]
    assert summary["overall"]["present"] == values.count("P")
    assert summary["overall"]["absent"] == values.count("A")
    assert summary["overall"]["no_attendance"] == values.count("NA")
    assert summary["overall"]["total"] == len(values)
    expected_by_subject = {}
    for day in generated:
        for slot in day["slots"]:
            if slot["status"] in {"P", "A", "NA"}:
                counts = expected_by_subject.setdefault(slot["subject_code"], {"P": 0, "A": 0, "NA": 0})
                counts[slot["status"]] += 1
    for subject in summary["subjects"]:
        counts = expected_by_subject[subject["subject_code"]]
        assert subject["present"] == counts["P"]
        assert subject["total"] == sum(counts.values())
    assert len(responses[3].json()["subjects"]) == 9
    assert {row["subject_code"]: row["alt_code"] for row in responses[3].json()["subjects"]
            if row["subject_code"] in {"BCS515B", "BCS506", "B**K507"}} == {
                "BCS515B": "BCS504B", "BCS506": "BCS505", "B**K507": "BCV508"}
    assert responses[4].json()["ledger"]["pending"] == responses[4].json()["ledger"]["to_be_collected"] - responses[4].json()["ledger"]["paid"]
    assert all(receipt["mode"] == "SYNTHETIC" and receipt["receipt_no"].startswith("SYN-")
               for year in responses[4].json()["years"] for receipt in year["receipts"])

    for username in ("fac1", "hod_cse", "admin1", "maint1"):
        headers = auth(m2_client, username)
        assert all(m2_client.get(path.split("?")[0], headers=headers).status_code == 403 for path in endpoints)

    with m2_client.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(TimetableSession)) == session_count_before_demo


def test_m7_erp_tuesday_evidence_and_wednesday_regression(m2_client):
    headers = auth(m2_client, "admin1")
    tuesday = m2_client.get("/timetable/date/2026-11-24", headers=headers).json()["sessions"]
    fifth_e = [row for row in tuesday if row["section_code"] == "E"]
    by_period = {(row["periods"][0], row["batch"]): row for row in fifth_e}
    assert by_period[(1, "ALL")]["subject_code"] == "BCS503"
    assert by_period[(1, "ALL")]["faculty_names"] == ["Ms. Swathi A"]
    assert by_period[(2, "ALL")]["subject_code"] == "BCS501"
    assert by_period[(2, "ALL")]["faculty_names"] == ["Mrs. Manasa Sandeep"]
    lab = by_period[(3, "B1")]
    assert lab["periods"] == [3, 4] and lab["subject_code"] == "BCS501"
    assert lab["session_type"] == "Lab"
    assert lab["faculty_names"] == ["Mrs. Manasa Sandeep", "Ashalatha N S"]
    assert lab["faculty_details"][1]["data_status"] == "REAL_ERP_SCREENSHOT"
    assert by_period[(3, "B2")]["block_id"] == lab["block_id"]
    assert by_period[(5, "ALL")]["faculty_names"] == ["Ms. Swathi A"]
    assert by_period[(6, "ALL")]["faculty_names"] == ["Mr. Parvathisha Pudugosula"]
    assert by_period[(7, "ALL")]["faculty_names"] == ["Dr. Deepak GB"]
    assert by_period[(7, "ALL")]["faculty_details"][0]["data_status"] == "REAL_ERP_SCREENSHOT"

    wednesday = m2_client.get("/timetable/date/2026-12-09", headers=headers).json()["sessions"]
    rows = [row for row in wednesday if row["section_code"] == "E"]
    indexed = {period: row for row in rows for period in row["periods"]}
    assert indexed[1]["subject_code"] == indexed[2]["subject_code"] == "BCS502"
    assert indexed[5]["subject_code"] == "BCS515B"
    assert indexed[6]["subject_code"] == "BCS501"
    assert indexed[5]["faculty_names"] == ["Mrs Usha CR"]
    assert indexed[6]["faculty_names"] == ["Mrs. Manasa Sandeep"]
