from __future__ import annotations

import heapq
import json
import math
from collections import defaultdict
from datetime import date as Date
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import AcademicTerm, Building, Holiday, NavEdge, NavNode, Room, TimetableSection, TimetableSession, TimetableSubject, User
from ..room_resolver import resolve_room

router = APIRouter(tags=["floorplan-navigation"])
ACTIVE_TERM = "2026-27-ODD"
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
DAY_SET = set(WEEKDAYS[:6])
LABELS = {-1: "Basement", 0: "Ground Floor", 1: "First Floor", 2: "Second Floor",
          3: "Third Floor", 4: "Fourth Floor", 5: "Fifth Floor"}
FLOORPLAN_PATH = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "floorplan.json"
DEFAULT_METRES_PER_PIXEL = 0.06


def _artifact() -> dict:
    return json.loads(FLOORPLAN_PATH.read_text(encoding="utf-8"))


def _color(room_type: str) -> str:
    kind = room_type.lower()
    if "washroom" in kind:
        return "#E2E8F0"
    if any(word in kind for word in ("computer lab", "hardware lab", "lab/classroom", "laboratory")):
        return "#D8B4FE"
    if any(word in kind for word in ("seminar", "conference", "workshop")):
        return "#86EFAC"
    if any(word in kind for word in ("faculty", "office", "admin", "admission", "principal", "staff room")):
        return "#FED7AA"
    if "classroom" in kind:
        return "#93C5FD"
    return "#CBD5E1"


def _weekday(day: str | None, date_value: Date | None) -> str | None:
    if date_value:
        return WEEKDAYS[date_value.weekday()]
    return day


def _node_label(node: NavNode) -> str:
    if node.node_type == "stairs_core_west":
        return "West stairs"
    if node.node_type == "stairs_core_east":
        return "East stairs"
    if node.node_type == "lifts_core_center":
        return "Center lift"
    if node.node_type.startswith("corridor_n"):
        return f"Corridor {node.node_type.removeprefix('corridor_').upper()}"
    if node.node_type == "door":
        return f"Door {node.room_id}"
    return node.node_type.replace("_", " ").title()


def _nav_node_out(node: NavNode) -> dict:
    return {"node_key": node.node_key, "kind": node.node_type, "floor": node.floor,
            "x": node.x, "y": node.y, "label": _node_label(node)}


def _room_aliases(room: Room) -> list[str]:
    return sorted(alias.alias for alias in room.aliases)


def _route_path_node(node: NavNode) -> dict:
    return {"node_key": node.node_key, "floor": node.floor, "x": node.x, "y": node.y,
            "kind": node.node_type, "label": _node_label(node)}


def _route_steps(path: list[dict], edges: list[dict]) -> list[dict]:
    by_key = {node["node_key"]: node for node in path}
    output = []
    for edge in edges:
        source, target = by_key[edge["from"]], by_key[edge["to"]]
        if edge["mode"] == "stairs":
            instruction = f"Take the stairs to Floor {target['floor']}"
        elif edge["mode"] == "lift":
            instruction = f"Take the lift to Floor {target['floor']}"
        else:
            instruction = f"Walk from {source['label']} to {target['label']}"
        output.append({"instruction": instruction, "floor": target["floor"],
                       "from_node": edge["from"], "to_node": edge["to"],
                       "distance_m": edge["distance_m"], "kind": edge["mode"]})
    return output


@router.get("/floorplan")
def list_floors(_user: User = Depends(get_current_user)):
    artifact = _artifact()
    return {
        "provenance": "SYNTHETIC",
        "canvas": {key: artifact["canvas"][key] for key in ("width", "height", "metres_per_pixel")},
        "floors": [{"floor": row["floor"], "label": row["label"], "room_count": row["room_count"]}
                   for row in artifact["floors"]],
    }


@router.get("/floorplan/{floor}")
def get_floorplan(
    floor: int,
    day: str | None = None,
    period: int | None = Query(None, ge=1, le=7),
    date_value: Date | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    if floor not in LABELS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Floor not found")
    if day and date_value:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Provide day or date, not both")
    if day is not None and day not in DAY_SET:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "day must be Mon through Sat")
    if (day is None) != (period is None) and date_value is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "day and period must be supplied together")
    if date_value is not None and period is None:
        # Holiday lookup is useful without a period; ordinary dates then have no occupancy context.
        time_filter = False
    else:
        time_filter = period is not None

    weekday = _weekday(day, date_value)
    holiday = db.scalar(select(Holiday).where(Holiday.holiday_date == date_value)) if date_value else None
    term = db.scalar(select(AcademicTerm).where(AcademicTerm.code == ACTIVE_TERM))
    if term is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Active term not found")

    room_colors = {row["room_id"]: row["color"]
                   for floor_row in _artifact()["floors"] for row in floor_row["rooms"]}
    rooms = list(db.scalars(
        select(Room).join(Building, Building.id == Room.building_id)
        .where(Building.code == "A", Room.floor == floor)
        .order_by(Room.number)
    ))
    room_outputs = []
    floor_nodes = list(db.scalars(select(NavNode).where(NavNode.floor == floor).order_by(NavNode.node_key)))
    core_by_type = {node.node_type: node for node in floor_nodes}
    cores = [{"x": core_by_type[kind].x - 40, "y": core_by_type[kind].y - 30, "w": 80, "h": 60,
              "label": _node_label(core_by_type[kind])}
             for kind in ("stairs_core_west", "lifts_core_center", "stairs_core_east") if kind in core_by_type]
    for room in rooms:
        if holiday or not time_filter:
            occupancy = {"occupied": False, "sessions": []} if holiday else None
        else:
            query = (select(TimetableSession, TimetableSection, TimetableSubject)
                     .join(TimetableSection, TimetableSection.id == TimetableSession.section_id)
                     .outerjoin(TimetableSubject, TimetableSubject.id == TimetableSession.subject_id)
                     .where(TimetableSession.term_id == term.id,
                            TimetableSession.room_id == room.id,
                            TimetableSession.day == weekday,
                            TimetableSession.start_period <= period,
                            TimetableSession.end_period >= period))
            rows = list(db.execute(query))
            sessions = [{
                "section_code": section.code, "batch": session.batch,
                "periods": list(range(session.start_period, session.end_period + 1)),
                "subject_code": subject.code if subject else None,
                "raw_label": session.raw_label,
            } for session, section, subject in rows]
            occupancy = {"occupied": bool(sessions), "sessions": sessions}

        unavailable = room.status in {"under_maintenance", "temporarily_unavailable"}
        room_outputs.append({
            "room_id": room.number,
            "geometry": {"x": room.x, "y": room.y, "w": room.w, "h": room.h},
            "color": room_colors.get(room.number, _color(room.room_type)),
            "status": room.status,
            "capacity_effective": 0 if unavailable else room.capacity,
            "data_status": room.provenance,
            "real_label": room.real_label,
            "aliases": _room_aliases(room),
            "occupancy": occupancy,
        })

    return {
        "floor": floor, "label": LABELS[floor],
        "canvas": {"width": 1000, "height": 600},
        "date": date_value.isoformat() if date_value else None,
        "weekday": weekday,
        "holiday": holiday.name if holiday else None,
        "cores": cores,
        "nav_nodes": [_nav_node_out(node) for node in floor_nodes],
        "rooms": room_outputs,
    }


def _edge_values(edge: NavEdge) -> tuple[float, float, float]:
    if edge.mode == "stairs":
        distance = settings.nav_stairs_metres_per_floor * max(edge.floor_delta, 1)
        wait = 0.0
    elif edge.mode == "lift":
        distance = settings.nav_lift_metres_per_floor * max(edge.floor_delta, 1)
        wait = settings.nav_lift_wait_seconds * max(edge.floor_delta, 1)
    else:
        distance = edge.distance_m * settings.nav_metres_per_pixel / DEFAULT_METRES_PER_PIXEL
        wait = 0.0
    weight = distance / settings.nav_walking_speed_mps + wait
    return distance, wait, weight


@router.get("/nav/route")
def nav_route(
    from_room: str = Query(alias="from"),
    to_room: str = Query(alias="to"),
    mode: Literal["stairs", "lift", "accessible"] = Query(...),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    canonical_from = resolve_room(from_room)
    canonical_to = resolve_room(to_room)
    if canonical_from is None or canonical_to is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown A-Block room")
    rooms = {row.number for row in db.scalars(select(Room).join(Building).where(Building.code == "A"))}
    if canonical_from not in rooms or canonical_to not in rooms:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
    doors = {node.room_id: node for node in db.scalars(select(NavNode).where(NavNode.room_id.in_({canonical_from, canonical_to})))}
    if canonical_from not in doors or canonical_to not in doors:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room door node not found")
    start, goal = doors[canonical_from].node_key, doors[canonical_to].node_key
    if canonical_from == canonical_to:
        start_node = doors[canonical_from]
        path = [_route_path_node(start_node)]
        return {"from_room": canonical_from, "to_room": canonical_to, "mode": mode,
                "node_keys": [start], "edges": [], "distance_m": 0,
                "route_cost_seconds": 0, "provenance": "SYNTHETIC", "path": path,
                "steps": [], "floors_visited": [start_node.floor]}

    nodes = list(db.scalars(select(NavNode)))
    nodes_by_id = {node.id: node for node in nodes}
    nodes_by_key = {node.node_key: node for node in nodes}
    allowed_modes = {"corridor", "stairs"} if mode == "stairs" else {"corridor", "lift"}
    adjacency: dict[str, list[tuple[str, NavEdge, float]]] = defaultdict(list)
    for edge in db.scalars(select(NavEdge)):
        if edge.mode not in allowed_modes:
            continue
        source, target = nodes_by_id[edge.from_node_id], nodes_by_id[edge.to_node_id]
        _distance, _wait, weight = _edge_values(edge)
        adjacency[source.node_key].append((target.node_key, edge, weight))
        if edge.bidirectional:
            adjacency[target.node_key].append((source.node_key, edge, weight))

    distances = {start: 0.0}
    parents: dict[str, tuple[str, NavEdge]] = {}
    heap = [(0.0, start)]
    while heap:
        current_cost, current = heapq.heappop(heap)
        if current_cost > distances.get(current, math.inf):
            continue
        if current == goal:
            break
        for neighbor, edge, weight in adjacency.get(current, []):
            new_cost = current_cost + weight
            if new_cost < distances.get(neighbor, math.inf):
                distances[neighbor] = new_cost
                parents[neighbor] = (current, edge)
                heapq.heappush(heap, (new_cost, neighbor))
    if goal not in distances:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No route found for this mode")

    reversed_steps = []
    cursor = goal
    while cursor != start:
        previous, edge = parents[cursor]
        reversed_steps.append((previous, cursor, edge))
        cursor = previous
    steps = list(reversed(reversed_steps))
    route_edges = []
    for source, target, edge in steps:
        distance, wait, weight = _edge_values(edge)
        route_edges.append({"from": source, "to": target, "mode": edge.mode,
                            "distance_m": round(distance, 4), "wait_seconds": round(wait, 4),
                            "weight": round(weight, 4)})
    route_nodes = [_route_path_node(nodes_by_key[key])
                   for key in [start, *[target for _, target, _ in steps]]]
    floors_visited = list(dict.fromkeys(node["floor"] for node in route_nodes))
    return {
        "from_room": canonical_from, "to_room": canonical_to, "mode": mode,
        "node_keys": [start, *[target for _, target, _ in steps]],
        "edges": route_edges,
        "distance_m": round(sum(edge["distance_m"] for edge in route_edges), 4),
        "route_cost_seconds": round(sum(edge["weight"] for edge in route_edges), 4),
        "provenance": "SYNTHETIC",
        "path": route_nodes,
        "steps": _route_steps(route_nodes, route_edges),
        "floors_visited": floors_visited,
    }
