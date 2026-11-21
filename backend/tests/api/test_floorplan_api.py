import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.seed import DEV_PASSWORD, seed


@pytest.fixture(scope="module")
def nav_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False)
    with SessionLocal() as db:
        seed(db)

    def override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    engine.dispose()


def auth(client, username):
    response = client.post("/auth/login", json={"username": username, "password": DEV_PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_all_authenticated_roles_can_read_floorplans_and_anonymous_is_401(nav_client):
    assert nav_client.get("/floorplan").status_code == 401
    assert nav_client.get("/floorplan/1").status_code == 401
    assert nav_client.get("/nav/route?from=101&to=102&mode=stairs").status_code == 401
    for username in ("1DT24CS248", "fac1", "hod_cse", "admin1", "maint1"):
        headers = auth(nav_client, username)
        floors = nav_client.get("/floorplan", headers=headers)
        assert floors.status_code == 200
        assert [row["floor"] for row in floors.json()["floors"]] == [-1, 0, 1, 2, 3, 4, 5]
        assert nav_client.get("/floorplan/1", headers=headers).status_code == 200


def test_floorplan_occupancy_and_holiday(nav_client):
    headers = auth(nav_client, "admin1")
    floor = nav_client.get("/floorplan/1?day=Wed&period=1", headers=headers)
    assert floor.status_code == 200, floor.text
    room = next(row for row in floor.json()["rooms"] if row["room_id"] == "A-F1-01")
    assert room["occupancy"]["occupied"] is True
    assert any(session["section_code"] == "E" and session["subject_code"] == "BCS502"
               for session in room["occupancy"]["sessions"])
    assert room["data_status"] in {"SYNTHETIC", "INFERRED"}

    holiday = nav_client.get("/floorplan/1?date=2026-11-10&period=1", headers=headers)
    assert holiday.status_code == 200
    assert holiday.json()["holiday"] == "Deepavali 2026"
    assert all(not row["occupancy"]["occupied"] and not row["occupancy"]["sessions"]
               for row in holiday.json()["rooms"])


def _route(client, headers, source, target, mode):
    return client.get(f"/nav/route?from={source}&to={target}&mode={mode}", headers=headers)


def test_same_floor_route_is_corridor_only_and_sums_edge_weights(nav_client):
    headers = auth(nav_client, "fac1")
    response = _route(nav_client, headers, "101", "102", "stairs")
    assert response.status_code == 200, response.text
    route = response.json()
    assert route["node_keys"] == ["f1_door_A-F1-01", "f1_corridor_n1", "f1_corridor_n2", "f1_door_A-F1-02"]
    assert route["distance_m"] == pytest.approx(sum(edge["distance_m"] for edge in route["edges"]))
    assert route["route_cost_seconds"] == pytest.approx(sum(edge["weight"] for edge in route["edges"]))
    assert all(edge["mode"] == "corridor" for edge in route["edges"])


def test_cross_floor_stairs_lift_accessible_and_alias_routes(nav_client):
    headers = auth(nav_client, "hod_cse")
    stairs = _route(nav_client, headers, "A-F1-01", "A-F3-05", "stairs")
    lift = _route(nav_client, headers, "A-F1-01", "A-F3-05", "lift")
    accessible = _route(nav_client, headers, "A-F1-01", "A-F3-05", "accessible")
    assert all(response.status_code == 200 for response in (stairs, lift, accessible))
    assert any(edge["mode"] == "stairs" for edge in stairs.json()["edges"])
    assert all(edge["mode"] != "lift" for edge in stairs.json()["edges"])
    assert any(edge["mode"] == "lift" for edge in lift.json()["edges"])
    assert all(edge["mode"] != "stairs" for edge in accessible.json()["edges"])
    assert any(edge["mode"] == "lift" for edge in accessible.json()["edges"])

    a108 = _route(nav_client, headers, "A-108", "305", "lift")
    seminar = _route(nav_client, headers, "SH-2", "305", "accessible")
    assert a108.status_code == 200 and a108.json()["from_room"] == "A-F1-10"
    assert seminar.status_code == 200 and seminar.json()["from_room"] == "A-G10"


def test_unknown_room_bad_mode_and_trivial_route(nav_client):
    headers = auth(nav_client, "maint1")
    assert _route(nav_client, headers, "not-a-room", "101", "stairs").status_code == 404
    assert nav_client.get("/nav/route?from=101&to=102&mode=hover", headers=headers).status_code == 422
    same = _route(nav_client, headers, "A-108", "A-F1-10", "accessible")
    assert same.status_code == 200
    assert same.json()["node_keys"] == ["f1_door_A-F1-10"]
    assert same.json()["edges"] == []
    assert same.json()["distance_m"] == same.json()["route_cost_seconds"] == 0
