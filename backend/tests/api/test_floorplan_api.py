import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import NavNode, Room, User
from app.seed import DEV_PASSWORD, seed


@pytest.fixture(scope="module")
def nav_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False)
    with SessionLocal() as db:
        seed(db)
        student_username = db.scalar(select(User.username).where(User.role == "student").order_by(User.username))

    def override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    client.student_username = student_username
    client.SessionLocal = SessionLocal
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
    for username in (nav_client.student_username, "fac1", "hod_cse", "admin1", "maint1"):
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


def test_floorplan_additive_map_contract_and_database_coordinates(nav_client):
    headers = auth(nav_client, "admin1")
    response = nav_client.get("/floorplan/3?day=Wed&period=1", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert {"floor", "label", "canvas", "date", "weekday", "holiday", "rooms"}.issubset(payload)
    assert (payload["floor"], payload["label"], payload["canvas"], payload["date"],
            payload["weekday"], payload["holiday"]) == (3, "Third Floor", {"width": 1000, "height": 600}, None, "Wed", None)
    assert {"cores", "nav_nodes"}.issubset(payload)
    assert [core["label"] for core in payload["cores"]] == ["West stairs", "Center lift", "East stairs"]
    for core in payload["cores"]:
        assert {"x", "y", "w", "h", "label"}.issubset(core)
    assert payload["nav_nodes"]
    for node in payload["nav_nodes"]:
        assert {"node_key", "kind", "floor", "x", "y", "label"}.issubset(node)
    room = next(row for row in payload["rooms"] if row["room_id"] == "A-F3-05")
    assert {"room_id", "geometry", "color", "status", "capacity_effective", "data_status", "occupancy"}.issubset(room)
    assert {key: room[key] for key in ("room_id", "geometry", "color", "status", "capacity_effective", "data_status", "occupancy")} == {
        "room_id": "A-F3-05", "geometry": {"x": 780.0, "y": 40.0, "w": 160.0, "h": 210.0},
        "color": "#D8B4FE", "status": "available", "capacity_effective": 30,
        "data_status": "SYNTHETIC", "occupancy": {"occupied": False, "sessions": []}}
    assert {"real_label", "aliases"}.issubset(room)
    assert room["real_label"] == "Computer Lab 05"
    assert room["aliases"] == ["305"]

    with nav_client.SessionLocal() as db:
        db_nodes = {node.node_key: node for node in db.query(NavNode).filter(NavNode.floor == 3)}
        assert set(db_nodes) == {node["node_key"] for node in payload["nav_nodes"]}
        for value in payload["nav_nodes"]:
            node = db_nodes[value["node_key"]]
            assert (value["floor"], value["x"], value["y"]) == (node.floor, node.x, node.y)
        for core in payload["cores"]:
            node = next(n for n in db_nodes.values() if _label_for_node(n.node_type) == core["label"])
            assert (core["x"] + 40, core["y"] + 30) == (node.x, node.y)


def _label_for_node(node_type):
    return {"stairs_core_west": "West stairs", "lifts_core_center": "Center lift",
            "stairs_core_east": "East stairs"}.get(node_type)


def test_rooms_roomout_adds_map_metadata_without_removing_old_fields(nav_client):
    headers = auth(nav_client, "fac1")
    response = nav_client.get("/rooms", headers=headers)
    assert response.status_code == 200
    room = next(row for row in response.json() if row["number"] == "A-F1-10")
    old_fields = {"id", "building_id", "number", "floor", "capacity", "room_type", "facilities",
                  "status", "version", "provenance"}
    assert old_fields.issubset(room)
    assert {"real_label", "aliases", "data_status", "capacity_effective"}.issubset(room)
    assert room["real_label"] == "Empty Room 10"
    assert room["aliases"] == ["110", "A-108"]
    assert room["data_status"] == room["provenance"] == "SYNTHETIC"
    assert room["capacity_effective"] == room["capacity"] == 30
    assert {key: room[key] for key in ("id", "building_id", "number", "floor", "capacity", "room_type", "facilities", "status", "version", "provenance")} == {
        "id": 24, "building_id": 1, "number": "A-F1-10", "floor": 1, "capacity": 30,
        "room_type": "Empty Room", "facilities": "", "status": "available", "version": 1,
        "provenance": "SYNTHETIC"}

    with nav_client.SessionLocal() as db:
        source = db.get(Room, room["id"])
        assert room["aliases"] == sorted(alias.alias for alias in source.aliases)


def _route(client, headers, source, target, mode):
    return client.get(f"/nav/route?from={source}&to={target}&mode={mode}", headers=headers)


def test_same_floor_route_is_corridor_only_and_sums_edge_weights(nav_client):
    headers = auth(nav_client, "fac1")
    response = _route(nav_client, headers, "101", "102", "stairs")
    assert response.status_code == 200, response.text
    route = response.json()
    assert route["node_keys"] == ["f1_door_A-F1-01", "f1_corridor_n1", "f1_corridor_n2", "f1_door_A-F1-02"]
    old_fields = {"from_room", "to_room", "mode", "node_keys", "edges", "distance_m", "route_cost_seconds", "provenance"}
    assert old_fields.issubset(route)
    assert {"path", "steps", "floors_visited"}.issubset(route)
    assert route["distance_m"] == pytest.approx(sum(edge["distance_m"] for edge in route["edges"]))
    assert route["distance_m"] == pytest.approx(sum(step["distance_m"] for step in route["steps"]))
    assert route["route_cost_seconds"] == pytest.approx(sum(edge["weight"] for edge in route["edges"]))
    assert all(edge["mode"] == "corridor" for edge in route["edges"])
    assert route["edges"] == [
        {"from": "f1_door_A-F1-01", "to": "f1_corridor_n1", "mode": "corridor", "distance_m": 3.0, "wait_seconds": 0.0, "weight": 2.5},
        {"from": "f1_corridor_n1", "to": "f1_corridor_n2", "mode": "corridor", "distance_m": 12.0, "wait_seconds": 0.0, "weight": 10.0},
        {"from": "f1_corridor_n2", "to": "f1_door_A-F1-02", "mode": "corridor", "distance_m": 3.0, "wait_seconds": 0.0, "weight": 2.5},
    ]
    assert (route["distance_m"], route["route_cost_seconds"], route["provenance"]) == (18.0, 15.0, "SYNTHETIC")
    assert [node["node_key"] for node in route["path"]] == route["node_keys"]
    with nav_client.SessionLocal() as db:
        db_nodes = {node.node_key: node for node in db.query(NavNode).all()}
        for value in route["path"]:
            node = db_nodes[value["node_key"]]
            assert (value["floor"], value["x"], value["y"]) == (node.floor, node.x, node.y)
            assert {"node_key", "floor", "x", "y", "kind", "label"}.issubset(value)
        for step in route["steps"]:
            assert {"instruction", "floor", "from_node", "to_node", "distance_m", "kind"}.issubset(step)


def test_cross_floor_stairs_lift_accessible_and_alias_routes(nav_client):
    headers = auth(nav_client, "hod_cse")
    stairs = _route(nav_client, headers, "A-F1-01", "A-F3-05", "stairs")
    lift = _route(nav_client, headers, "A-F1-01", "A-F3-05", "lift")
    accessible = _route(nav_client, headers, "A-F1-01", "A-F3-05", "accessible")
    assert all(response.status_code == 200 for response in (stairs, lift, accessible))
    assert any(edge["mode"] == "stairs" for edge in stairs.json()["edges"])
    assert all(edge["mode"] != "lift" for edge in stairs.json()["edges"])
    assert any(edge["mode"] == "lift" for edge in lift.json()["edges"])
    assert lift.json()["floors_visited"] == [1, 2, 3]
    assert set(lift.json()["floors_visited"]) >= {1, 3}
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


def test_m7_navigation_instructions_are_human_readable_additive_and_indexed(nav_client):
    headers = auth(nav_client, "fac1")
    response = _route(nav_client, headers, "A-G06", "A-F5-05", "accessible")
    assert response.status_code == 200
    route = response.json()
    old_fields = {"from_room", "to_room", "mode", "node_keys", "edges", "distance_m",
                  "route_cost_seconds", "provenance", "path", "steps", "floors_visited"}
    assert old_fields.issubset(route)
    instructions = route["instructions"]
    assert [row["kind"] for row in instructions] == ["start", "walk", "lift", "walk", "arrive"]
    assert instructions[0]["text"] == "Leave Staff Room 06 (A-G06)"
    assert instructions[1]["text"] == "Walk 27 m along the Ground Floor corridor towards the Lift."
    assert instructions[3]["text"] == "Walk 27 m along the Floor 5 corridor towards Computer Lab 05 (A-F5-05)."
    assert instructions[-1]["text"] == "You have arrived at Computer Lab 05 (A-F5-05)"
    assert instructions[2]["text"] == "Take the Lift up 5 floors to Floor 5."
    assert all("corridor_" not in row["text"] and "door_" not in row["text"]
               and "stairs_core_" not in row["text"] and "lifts_core_" not in row["text"]
               for row in instructions)
    assert len(instructions) < len(route["steps"])
    assert all(0 <= row["path_from_index"] <= row["path_to_index"] < len(route["path"])
               for row in instructions)
    assert sum(row["distance_m"] for row in instructions) == pytest.approx(route["distance_m"], abs=0.5)
    assert route["summary"]["floors_traversed"] == [0, 1, 2, 3, 4, 5]
    assert route["summary"]["floors_changed"] == 5
    assert route["summary"]["est_minutes"] == 3
    assert all(row["kind"] != "stairs" for row in instructions)

    same = _route(nav_client, headers, "A-108", "A-F1-10", "accessible").json()
    assert [row["kind"] for row in same["instructions"]] == ["arrive"]
    assert same["instructions"][0]["path_from_index"] == same["instructions"][0]["path_to_index"] == 0
    for source, target in (("A-108", "305"), ("SH-2", "A-F5-05")):
        assert _route(nav_client, headers, source, target, "lift").status_code == 200
