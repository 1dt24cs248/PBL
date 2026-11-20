"""Deterministic synthetic geometry and indoor navigation graph generator."""
from __future__ import annotations

import math

from .dataset import Dataset, parse_dataset

WIDTH = 1000
HEIGHT = 600
CORRIDOR = {"x": 0, "y": 270, "w": WIDTH, "h": 60}
CORRIDOR_XS = (100, 300, 500, 700, 900)
METRES_PER_PIXEL = 0.06
FLOOR_LABELS = {
    -1: "Basement", 0: "Ground Floor", 1: "First Floor", 2: "Second Floor",
    3: "Third Floor", 4: "Fourth Floor", 5: "Fifth Floor",
}
COLORS = {
    "classroom": "#93C5FD",
    "lab": "#D8B4FE",
    "seminar": "#86EFAC",
    "office": "#FED7AA",
    "utility": "#CBD5E1",
    "washroom": "#E2E8F0",
}


def _room_color(facility_type: str) -> str:
    kind = facility_type.lower()
    if "washroom" in kind or "toilet" in kind:
        return COLORS["washroom"]
    if any(word in kind for word in ("computer lab", "hardware lab", "lab/classroom", "laboratory")):
        return COLORS["lab"]
    if any(word in kind for word in ("seminar", "conference", "workshop")):
        return COLORS["seminar"]
    if any(word in kind for word in ("faculty", "office", "admin", "admission", "principal", "staff room")):
        return COLORS["office"]
    if "classroom" in kind:
        return COLORS["classroom"]
    return COLORS["utility"]


def _node(floor: int, node_type: str, x: float, y: float,
          room_id: str | None = None) -> dict:
    if room_id:
        key = f"f{floor}_door_{room_id}"
    else:
        key = f"f{floor}_{node_type}"
    if node_type.startswith("corridor_"):
        color = "#E2E8F0"
    else:
        color = "#CBD5E1"
    return {"node_key": key, "floor": floor, "node_type": node_type,
            "x": round(x, 2), "y": round(y, 2), "room_id": room_id,
            "color": color, "provenance": "SYNTHETIC"}


def _edge(source: str, target: str, *, mode: str, distance_m: float = 0,
          floor_delta: int = 0, wait_seconds: float = 0) -> dict:
    return {"from": source, "to": target, "mode": mode,
            "distance_m": round(distance_m, 4), "floor_delta": floor_delta,
            "wait_seconds": wait_seconds, "bidirectional": True,
            "provenance": "SYNTHETIC"}


def generate_floorplan(dataset: Dataset | None = None) -> dict:
    data = dataset or parse_dataset()
    by_floor: dict[int, list[dict]] = {floor: [] for floor in FLOOR_LABELS}
    for room in data.rooms:
        by_floor[room["floor_number"]].append(room)

    floors = []
    edges = []
    for floor in FLOOR_LABELS:
        rows = sorted(by_floor[floor], key=lambda row: row["room_id"])
        columns = max(1, math.ceil(len(rows) / 2))
        slot_width = 900 / columns
        floor_rooms = []
        nodes = [
            _node(floor, "stairs_core_west", 100, 300),
            _node(floor, "lifts_core_center", 500, 300),
            _node(floor, "stairs_core_east", 900, 300),
            *[_node(floor, f"corridor_n{index}", x, 300)
              for index, x in enumerate(CORRIDOR_XS, 1)],
        ]
        for index, room in enumerate(rows):
            row_index = 0 if index < columns else 1
            column_index = index if row_index == 0 else index - columns
            x = 50 + column_index * slot_width + 10
            y = 40 if row_index == 0 else 350
            w = slot_width - 20
            h = 210
            room_id = room["room_id"]
            color = _room_color(room["facility_type"])
            floor_rooms.append({
                "room_id": room_id,
                "geometry": {"x": round(x, 2), "y": y, "w": round(w, 2), "h": h},
                "color": color,
                "provenance": "SYNTHETIC",
            })
            door_y = y + h if row_index == 0 else y
            nearest_x = min(CORRIDOR_XS, key=lambda candidate: abs(candidate - (x + w / 2)))
            door_x = min(max(nearest_x, x), x + w)
            door = _node(floor, "door", door_x, door_y, room_id)
            nodes.append(door)
            nearest = min(range(1, 6), key=lambda n: abs(CORRIDOR_XS[n - 1] - door_x))
            corridor_key = f"f{floor}_corridor_n{nearest}"
            px_distance = math.hypot(door_x - CORRIDOR_XS[nearest - 1], door_y - 300)
            edges.append(_edge(door["node_key"], corridor_key, mode="corridor",
                               distance_m=px_distance * METRES_PER_PIXEL))

        floors.append({
            "floor": floor, "label": FLOOR_LABELS[floor], "room_count": len(floor_rooms),
            "canvas": {"width": WIDTH, "height": HEIGHT,
                       "metres_per_pixel": METRES_PER_PIXEL,
                       "corridor": dict(CORRIDOR), "room_rows": [{"y": 40, "h": 210}, {"y": 350, "h": 210}]},
            "rooms": floor_rooms, "nodes": nodes,
        })

        for left, right in zip(range(1, 5), range(2, 6)):
            distance = abs(CORRIDOR_XS[right - 1] - CORRIDOR_XS[left - 1]) * METRES_PER_PIXEL
            edges.append(_edge(f"f{floor}_corridor_n{left}", f"f{floor}_corridor_n{right}",
                               mode="corridor", distance_m=distance))
        for core, corridor in (("stairs_core_west", "corridor_n1"),
                               ("lifts_core_center", "corridor_n3"),
                               ("stairs_core_east", "corridor_n5")):
            edges.append(_edge(f"f{floor}_{core}", f"f{floor}_{corridor}", mode="corridor"))

    floors_sorted = sorted(FLOOR_LABELS)
    for lower, upper in zip(floors_sorted, floors_sorted[1:]):
        for core in ("stairs_core_west", "stairs_core_east"):
            edges.append(_edge(f"f{lower}_{core}", f"f{upper}_{core}", mode="stairs",
                               distance_m=12, floor_delta=1))
        edges.append(_edge(f"f{lower}_lifts_core_center", f"f{upper}_lifts_core_center",
                           mode="lift", distance_m=8, floor_delta=1, wait_seconds=20))

    return {
        "provenance": "SYNTHETIC",
        "generated_by": "backend/app/floorplan_generator.py",
        "canvas": {"width": WIDTH, "height": HEIGHT, "metres_per_pixel": METRES_PER_PIXEL,
                   "corridor": dict(CORRIDOR)},
        "colors": dict(COLORS), "floors": floors, "edges": edges,
    }
