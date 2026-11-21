from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_roles
from ..models import (AcademicTerm, OptimizerProposal, Room, TimetableSection,
                      TimetableSession, User)

router = APIRouter(prefix="/proposals", tags=["proposals"])


def _proposal(db: Session, proposal_id: str, *, lock: bool = False) -> OptimizerProposal:
    query = select(OptimizerProposal).where(OptimizerProposal.id == proposal_id)
    if lock:
        query = query.with_for_update()
    row = db.scalar(query)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposal not found")
    return row


def _full(row: OptimizerProposal) -> dict:
    return {**row.payload, "status": row.status}


@router.get("")
def list_proposals(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    rows = db.scalars(select(OptimizerProposal).order_by(OptimizerProposal.id))
    return [{"id": row.id, "status": row.status,
             "term_code": row.payload.get("term_code"),
             "solver_status": row.payload.get("solver_status"),
             "data_status": row.payload.get("data_status", "SYNTHETIC")} for row in rows]


@router.get("/{proposal_id}")
def get_proposal(proposal_id: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return _full(_proposal(db, proposal_id))


@router.post("/{proposal_id}/submit")
def submit(proposal_id: str, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin"))):
    row = _proposal(db, proposal_id, lock=True)
    if row.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only draft proposals can be submitted")
    if row.payload.get("solver_status") not in {"OPTIMAL", "FEASIBLE"} or not row.payload.get("validator", {}).get("valid", False):
        raise HTTPException(status.HTTP_409_CONFLICT, "Only validated feasible proposals can be submitted")
    row.status = "submitted"
    db.commit()
    return {"id": row.id, "status": row.status, "term_code": row.payload["term_code"], "data_status": "SYNTHETIC"}


@router.post("/{proposal_id}/approve")
def approve(proposal_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = _proposal(db, proposal_id)
    if user.role not in {"admin", "hod"}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    if user.role == "hod":
        affected = set(row.payload.get("affected_sections", []))
        sections = list(db.scalars(select(TimetableSection).where(
            TimetableSection.term_id == row.term_id,
            TimetableSection.code.in_(affected) if affected else False)))
        if not affected or len(sections) != len(affected) or any(
            not (section.division_code or "").startswith(f"{user.department or ''}-") for section in sections
        ):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "HOD may approve only proposals in their department")
    if row.status != "submitted":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only submitted proposals can be approved")
    row.status = "approved"
    db.commit()
    return {"id": row.id, "status": row.status, "term_code": row.payload["term_code"], "data_status": "SYNTHETIC"}


@router.post("/{proposal_id}/reject")
def reject(proposal_id: str, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin"))):
    row = _proposal(db, proposal_id)
    if row.status not in {"draft", "submitted"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Proposal cannot be rejected in its current state")
    row.status = "rejected"
    db.commit()
    return {"id": row.id, "status": row.status, "term_code": row.payload["term_code"], "data_status": "SYNTHETIC"}


@router.post("/{proposal_id}/apply")
def apply(proposal_id: str, db: Session = Depends(get_db), _user: User = Depends(require_roles("admin"))):
    row = _proposal(db, proposal_id, lock=True)
    if row.status != "approved":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only approved proposals can be applied")
    changes = row.payload.get("changes", [])
    session_ids = [change["session_id"] for change in changes]
    sessions = {session.id: session for session in db.scalars(
        select(TimetableSession).where(TimetableSession.id.in_(session_ids)).with_for_update())} if session_ids else {}
    room_numbers = {name for change in changes for name in (change["from_room"], change["to_room"])}
    rooms_by_number = {room.number: room for room in db.scalars(
        select(Room).where(Room.number.in_(room_numbers)).with_for_update())} if room_numbers else {}
    affected_rooms = {}
    for change in changes:
        session = sessions.get(change["session_id"])
        old_room, new_room = rooms_by_number.get(change["from_room"]), rooms_by_number.get(change["to_room"])
        if (session is None or old_room is None or new_room is None
            or session.version != change["expected_session_version"]
            or session.room_id != old_room.id
            or old_room.version != change["expected_from_room_version"]
            or new_room.version != change["expected_to_room_version"]):
            db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "version conflict")
        affected_rooms[old_room.id] = old_room
        affected_rooms[new_room.id] = new_room
    for change in changes:
        session = sessions[change["session_id"]]
        session.room_id = rooms_by_number[change["to_room"]].id
        session.room_inferred = False
        session.version += 1
    for room in affected_rooms.values():
        room.version += 1
    row.status = "applied"
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"id": row.id, "status": row.status, "term_code": row.payload["term_code"], "data_status": "SYNTHETIC"}
