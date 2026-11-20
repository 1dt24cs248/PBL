from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_roles
from ..models import ROOM_STATUSES, Building, Room, User
from ..schemas import RoomCreate, RoomOut, RoomStatusUpdate

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomOut])
def list_rooms(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = select(Room).order_by(Room.floor, Room.number)
    if status_filter:
        q = q.where(Room.status == status_filter)
    return list(db.scalars(q))


@router.post("", response_model=RoomOut, status_code=201)
def create_room(
    body: RoomCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles("admin")),
):
    if db.get(Building, body.building_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Building not found")
    exists = db.scalar(
        select(Room).where(
            Room.building_id == body.building_id, Room.number == body.number
        )
    )
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Room number already exists")
    room = Room(**body.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.patch("/{room_id}/status", response_model=RoomOut)
def update_room_status(
    room_id: int,
    body: RoomStatusUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles("admin")),
):
    if body.status not in ROOM_STATUSES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"status must be one of {list(ROOM_STATUSES)}",
        )
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
    room.status = body.status
    room.version += 1
    db.commit()
    db.refresh(room)
    return room