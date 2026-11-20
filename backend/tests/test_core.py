import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.seed import DEV_PASSWORD, seed
from app.models import Building, Room
from sqlalchemy import select


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    with Session() as s:
        seed(s)
        assert s.query(Room).count() == 66
        assert {b.code for b in s.scalars(select(Building))} == {"A"}

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def login(client, username):
    r = client.post("/auth/login", json={"username": username, "password": DEV_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_login_ok_and_category(client):
    r = client.post("/auth/login", json={"username": "hod_cse", "password": DEV_PASSWORD})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "hod"
    assert r.json()["user"]["category"] == "Faculty"


def test_login_wrong_password(client):
    r = client.post("/auth/login", json={"username": "stu1", "password": "nope"})
    assert r.status_code == 401


def test_no_token_is_401(client):
    assert client.get("/rooms").status_code == 401


def test_me(client):
    r = client.get("/auth/me", headers=login(client, "stu1"))
    assert r.json()["username"] == "stu1"


def test_student_can_list_rooms(client):
    r = client.get("/rooms", headers=login(client, "stu1"))
    assert r.status_code == 200 and len(r.json()) == 66
    assert {room["provenance"] for room in r.json()} == {"SYNTHETIC", "INFERRED"}


def test_student_cannot_create_room(client):
    r = client.post(
        "/rooms",
        headers=login(client, "stu1"),
        json={"building_id": 1, "number": "A999", "floor": 1, "capacity": 40},
    )
    assert r.status_code == 403


def test_hod_is_not_admin(client):
    assert client.get("/admin/users", headers=login(client, "hod_cse")).status_code == 403


def test_admin_creates_room_and_duplicate_rejected(client):
    h = login(client, "admin1")
    body = {"building_id": 1, "number": "A999", "floor": 3, "capacity": 40}
    assert client.post("/rooms", headers=h, json=body).status_code == 201
    assert client.post("/rooms", headers=h, json=body).status_code == 409


def test_status_update_bumps_version_and_validates(client):
    h = login(client, "admin1")
    r = client.patch("/rooms/1/status", headers=h, json={"status": "under_maintenance"})
    assert r.status_code == 200
    assert r.json()["status"] == "under_maintenance" and r.json()["version"] == 2
    bad = client.patch("/rooms/1/status", headers=h, json={"status": "flying"})
    assert bad.status_code == 422


def test_faculty_cannot_change_status(client):
    r = client.patch(
        "/rooms/1/status", headers=login(client, "fac1"), json={"status": "available"}
    )
    assert r.status_code == 403
