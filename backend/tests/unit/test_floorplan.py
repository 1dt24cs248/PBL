from collections import defaultdict, deque

from app.dataset import parse_dataset
from app.floorplan_generator import generate_floorplan


def test_every_room_has_a_door_connected_to_a_corridor_node():
    artifact = generate_floorplan(parse_dataset())
    rooms = {room["room_id"] for floor in artifact["floors"] for room in floor["rooms"]}
    nodes = {node["node_key"]: node for floor in artifact["floors"] for node in floor["nodes"]}
    door_rooms = {node["room_id"] for node in nodes.values() if node["node_type"] == "door"}
    assert door_rooms == rooms

    edges = artifact["edges"]
    for node in nodes.values():
        if node["node_type"] != "door":
            continue
        linked = [edge for edge in edges if node["node_key"] in (edge["from"], edge["to"])]
        assert len(linked) == 1
        other_key = linked[0]["to"] if linked[0]["from"] == node["node_key"] else linked[0]["from"]
        assert nodes[other_key]["node_type"].startswith("corridor_")


def test_navigation_graph_is_connected_and_vertical_cores_align():
    artifact = generate_floorplan()
    adjacency = defaultdict(set)
    nodes = [node for floor in artifact["floors"] for node in floor["nodes"]]
    for edge in artifact["edges"]:
        adjacency[edge["from"]].add(edge["to"])
        adjacency[edge["to"]].add(edge["from"])
    seen = set()
    queue = deque([nodes[0]["node_key"]])
    while queue:
        node = queue.popleft()
        if node in seen:
            continue
        seen.add(node)
        queue.extend(adjacency[node] - seen)
    assert seen == {node["node_key"] for node in nodes}

    for core in ("stairs_core_west", "lifts_core_center", "stairs_core_east"):
        x_positions = {node["x"] for node in nodes if node["node_type"] == core}
        assert len(x_positions) == 1
    assert {floor["floor"] for floor in artifact["floors"]} == {-1, 0, 1, 2, 3, 4, 5}


def test_room_layout_uses_required_canvas_corridor_rows_and_colors():
    artifact = generate_floorplan()
    assert artifact["provenance"] == "SYNTHETIC"
    assert artifact["canvas"]["width"] == 1000 and artifact["canvas"]["height"] == 600
    assert artifact["canvas"]["corridor"] == {"x": 0, "y": 270, "w": 1000, "h": 60}
    expected_colors = {"classroom": "#93C5FD", "lab": "#D8B4FE", "seminar": "#86EFAC",
                       "office": "#FED7AA", "utility": "#CBD5E1", "washroom": "#E2E8F0"}
    assert artifact["colors"] == expected_colors
    for floor in artifact["floors"]:
        assert floor["canvas"]["room_rows"] == [{"y": 40, "h": 210}, {"y": 350, "h": 210}]
