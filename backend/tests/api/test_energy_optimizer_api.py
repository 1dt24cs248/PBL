from contextlib import redirect_stdout
from io import StringIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import (AcademicTerm, OptimizerProposal, Room, TimetableSession,
                        User)
from app.seed import DEV_PASSWORD, seed


@pytest.fixture
def m5_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    local = sessionmaker(bind=engine, autoflush=False)
    with local() as db, redirect_stdout(StringIO()):
        seed(db)

    def override():
        db = local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()


def auth(client, username):
    response = client.post("/auth/login", json={"username": username, "password": DEV_PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_energy_endpoints_and_role_permissions(m5_client):
    client = m5_client
    assert client.get("/energy/baseline").status_code == 401
    assert client.get("/energy/utilization").status_code == 401
    admin = auth(client, "admin1")
    hod = auth(client, "hod_cse")
    student = auth(client, "stu1")
    faculty = auth(client, "fac1")
    maintenance = auth(client, "maint1")
    baseline = client.get("/energy/baseline?term=2026-27-ODD", headers=admin)
    utilization = client.get("/energy/utilization?term=2026-27-ODD", headers=hod)
    assert baseline.status_code == 200 and baseline.json()["data_status"] == "SYNTHETIC"
    assert utilization.status_code == 200 and utilization.json()["days_per_week"] == 6
    for path in ("/energy/baseline", "/energy/utilization"):
        assert client.get(path, headers=student).status_code == 403
        assert client.get(path, headers=faculty).status_code == 403
        assert client.get(path, headers=maintenance).status_code == 403
    request = {"term": "2026-27-ODD", "time_limit_s": 1}
    assert client.post("/optimizer/energy", json=request).status_code == 401
    assert client.post("/optimizer/energy", headers=student, json=request).status_code == 403
    assert client.post("/optimizer/energy", headers=faculty, json=request).status_code == 403
    assert client.post("/optimizer/energy", headers=hod, json=request).status_code == 403
    assert client.post("/optimizer/energy", headers=maintenance, json=request).status_code == 403
    assert client.get("/timetable/student/me", headers=maintenance).status_code == 403
    manual_session = {"term_code": "2026-27-ODD", "section_code": "A", "batch": "ALL", "day": "Sat",
        "periods": [7], "subject_code": "TEST", "room_id": "A-F1-01", "room_required": True,
        "raw_label": "synthetic role test"}
    assert client.post("/timetable/sessions", headers=student, json=manual_session).status_code == 403
    assert client.post("/timetable/sessions", headers=faculty, json=manual_session).status_code == 403
    assert client.post("/proposals/missing/submit", headers=student).status_code == 403
    assert client.post("/optimizer/energy", headers=admin, json={"term": "missing"}).status_code == 404


def test_rejected_proposal_changes_nothing_and_stale_apply_returns_409(m5_client):
    client = m5_client
    admin_headers = auth(client, "admin1")
    # Build proposal and version changes through the test's dependency session.
    override = app.dependency_overrides[get_db]
    db = next(override())
    try:
        term = db.scalar(select(AcademicTerm).where(AcademicTerm.code == "2026-27-ODD"))
        session = db.scalar(select(TimetableSession).where(TimetableSession.term_id == term.id,
                                                          TimetableSession.room_id.is_not(None)))
        old_room = db.get(Room, session.room_id)
        new_room = db.scalar(select(Room).where(Room.id != old_room.id))
        admin = db.scalar(select(User).where(User.username == "admin1"))
        old_version = session.version
        payload = {"id": "rejected-proposal", "term_code": term.code, "solver_status": "OPTIMAL",
            "data_status": "SYNTHETIC", "affected_sections": [], "changes": [{
                "session_id": session.id, "from_room": old_room.number, "to_room": new_room.number,
                "expected_session_version": session.version, "expected_from_room_version": old_room.version,
                "expected_to_room_version": new_room.version}]}
        db.add(OptimizerProposal(id="rejected-proposal", term_id=term.id, status="draft", payload=payload,
                                 created_by=admin.id, provenance="SYNTHETIC"))
        db.commit()
        before_room_id = session.room_id
        rejected = client.post("/proposals/rejected-proposal/reject", headers=admin_headers)
        assert rejected.status_code == 200
        db.refresh(session)
        assert session.room_id == before_room_id and session.version == old_version
        assert client.get("/proposals/rejected-proposal", headers=admin_headers).json()["status"] == "rejected"

        stale_payload = dict(payload, id="stale-proposal")
        db.add(OptimizerProposal(id="stale-proposal", term_id=term.id, status="approved", payload=stale_payload,
                                 created_by=admin.id, provenance="SYNTHETIC"))
        session.version += 1
        db.commit()
        stale = client.post("/proposals/stale-proposal/apply", headers=admin_headers)
        assert stale.status_code == 409
        db.refresh(session)
        assert session.room_id == before_room_id

        success_payload = dict(payload, id="apply-proposal")
        success_payload["changes"] = [dict(payload["changes"][0],
            expected_session_version=session.version, expected_from_room_version=old_room.version,
            expected_to_room_version=new_room.version)]
        db.add(OptimizerProposal(id="apply-proposal", term_id=term.id, status="approved", payload=success_payload,
                                 created_by=admin.id, provenance="SYNTHETIC"))
        db.commit()
        applied = client.post("/proposals/apply-proposal/apply", headers=admin_headers)
        assert applied.status_code == 200
        assert applied.json()["status"] == "applied"
        db.refresh(session)
        assert session.room_id == new_room.id and session.version == old_version + 2
    finally:
        db.close()


def test_hod_approval_is_department_scoped(m5_client):
    client = m5_client
    hod_headers = auth(client, "hod_cse")
    override = app.dependency_overrides[get_db]
    db = next(override())
    try:
        term = db.scalar(select(AcademicTerm).where(AcademicTerm.code == "2026-27-ODD"))
        admin = db.scalar(select(User).where(User.username == "admin1"))
        hod = db.scalar(select(User).where(User.username == "hod_cse"))
        payload = {"id": "department-approval", "term_code": term.code, "affected_sections": ["A"],
                   "changes": [], "solver_status": "OPTIMAL", "data_status": "SYNTHETIC"}
        db.add(OptimizerProposal(id="department-approval", term_id=term.id, status="submitted",
                                 payload=payload, created_by=admin.id, provenance="SYNTHETIC"))
        hod.department = "ECE"
        db.commit()
        assert client.post("/proposals/department-approval/approve", headers=hod_headers).status_code == 403
        hod.department = "CSE"
        db.commit()
        assert client.post("/proposals/department-approval/approve", headers=hod_headers).status_code == 200
    finally:
        db.close()
