from __future__ import annotations

from datetime import date as Date
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_roles
from ..models import (
    AcademicTerm, DivisionSectionMap, Faculty, Holiday, Room, Student,
    TimetableSection, TimetableSession, TimetableSessionFaculty,
    TimetableSubject, User,
)
from ..room_resolver import resolve_room
from ..schemas import TimetableSessionCreate, TimetableSessionPatch
from ..timetable_import import detect_conflicts

router = APIRouter(tags=["timetable"])
ACTIVE_TERM = "2026-27-ODD"
DAYS = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat"}


def _term(db: Session, code: str | None) -> AcademicTerm:
    term_code = code or ACTIVE_TERM
    term = db.scalar(select(AcademicTerm).where(AcademicTerm.code == term_code))
    if term is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Term not found")
    return term


def _section(db: Session, term_id: int, code: str) -> TimetableSection:
    row = db.scalar(select(TimetableSection).where(TimetableSection.term_id == term_id,
                                                   TimetableSection.code == code))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Section not found")
    return row


def _faculty_codes(db: Session, session_row: TimetableSession) -> list[Faculty]:
    return list(db.scalars(
        select(Faculty)
        .join(TimetableSessionFaculty, TimetableSessionFaculty.faculty_id == Faculty.id)
        .where(TimetableSessionFaculty.session_id == session_row.id)
        .order_by(Faculty.id)
    ))


def _session_out(db: Session, row: TimetableSession) -> dict:
    term = db.get(AcademicTerm, row.term_id)
    section = db.get(TimetableSection, row.section_id)
    subject = db.get(TimetableSubject, row.subject_id) if row.subject_id else None
    faculty = db.get(Faculty, row.faculty_id) if row.faculty_id else None
    room = db.get(Room, row.room_id) if row.room_id else None
    return {
        "id": row.id,
        "term_code": term.code,
        "section_code": section.code,
        "batch": row.batch,
        "day": row.day,
        "periods": list(range(row.start_period, row.end_period + 1)),
        "subject_code": subject.code if subject else None,
        "subject_name": subject.name if subject else None,
        "faculty_id": faculty.id if faculty else None,
        "faculty_initials": faculty.initials if faculty else None,
        "faculty_name": faculty.full_name if faculty else None,
        "room_id": room.number if room else None,
        "room_required": row.room_required,
        "raw_label": row.raw_label,
        "block_id": row.block_id,
        "provenance": row.provenance,
        "version": row.version,
    }


def _session_inputs(db: Session, term_id: int, *, exclude_id: int | None = None) -> list[dict]:
    query = select(TimetableSession).where(TimetableSession.term_id == term_id)
    if exclude_id is not None:
        query = query.where(TimetableSession.id != exclude_id)
    rows = list(db.scalars(query))
    terms = {term.id: term.code for term in db.scalars(select(AcademicTerm))}
    sections = {section.id: section.code for section in db.scalars(select(TimetableSection))}
    rooms = {room.id: room.number for room in db.scalars(select(Room))}
    faculty_ids = set(db.scalars(
        select(TimetableSessionFaculty.faculty_id)
        .join(TimetableSession, TimetableSession.id == TimetableSessionFaculty.session_id)
        .where(TimetableSession.term_id == term_id)
    ))
    faculty_by_id = {row.id: row.initials for row in db.scalars(select(Faculty).where(Faculty.id.in_(faculty_ids)))} if faculty_ids else {}
    linked: dict[int, list[str]] = {}
    for session_id, faculty_id in db.execute(
        select(TimetableSessionFaculty.session_id, TimetableSessionFaculty.faculty_id)
        .join(TimetableSession, TimetableSession.id == TimetableSessionFaculty.session_id)
        .where(TimetableSession.term_id == term_id)
    ):
        linked.setdefault(session_id, []).append(faculty_by_id[faculty_id])
    return [{
        "id": row.id,
        "term_code": terms[row.term_id],
        "section_code": sections[row.section_id],
        "batch": row.batch,
        "day": row.day,
        "start_period": row.start_period,
        "end_period": row.end_period,
        "faculty_initials": linked.get(row.id, []),
        "room_id": rooms.get(row.room_id) if row.room_id else None,
        "room_required": row.room_required,
        "block_id": row.block_id,
    } for row in rows]


def _db_conflicts(db: Session, term_id: int, *, exclude_id: int | None = None) -> list[dict]:
    sessions = _session_inputs(db, term_id, exclude_id=exclude_id)
    conflicts = detect_conflicts(sessions)
    for conflict in conflicts:
        conflict["session_ids"] = [sessions[index]["id"] for index in conflict.pop("session_indices")]
    return conflicts


def _write_conflict_for(candidate: dict, existing: list[dict]) -> dict | None:
    candidates = existing + [candidate]
    index = len(candidates) - 1
    for conflict in detect_conflicts(candidates):
        indices = conflict["session_indices"]
        if index in indices:
            return {key: value for key, value in conflict.items() if key != "session_indices"} | {
                "session_ids": [candidates[i].get("id") for i in indices]
            }
    return None


def _validated_session_refs(db: Session, term: AcademicTerm, section_code: str,
                            subject_code: str, faculty_id: int | None, room_token: str | None):
    section = _section(db, term.id, section_code)
    subject = db.scalar(select(TimetableSubject).where(TimetableSubject.term_id == term.id,
                                                       TimetableSubject.code == subject_code))
    if subject is None:
        subject = TimetableSubject(term_id=term.id, code=subject_code, name=subject_code, provenance="SYNTHETIC")
        db.add(subject)
        db.flush()
    faculty = db.get(Faculty, faculty_id) if faculty_id else None
    if faculty_id and (faculty is None or faculty.term_id != term.id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Faculty does not belong to term")
    room = None
    if room_token:
        canonical = resolve_room(room_token)
        room = db.scalar(select(Room).where(Room.number == canonical)) if canonical else None
        if room is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown A-Block room")
    return section, subject, faculty, room


def _validate_times(day: str, periods: list[int], batch: str, room_required: bool, room_id: str | None):
    if day not in DAYS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "day must be Mon through Sat")
    if not periods or any(period < 1 or period > 7 for period in periods):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "periods must contain values from 1 through 7")
    if sorted(set(periods)) != list(range(min(periods), max(periods) + 1)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "periods must be contiguous")
    if batch not in {"ALL", "B1", "B2"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "batch must be ALL, B1, or B2")
    if room_required and not room_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "room_id is required")
    if not room_required and room_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "roomless sessions cannot set room_id")


@router.get("/sections")
def list_sections(term: str | None = None, db: Session = Depends(get_db),
                  _user: User = Depends(get_current_user)):
    query = select(TimetableSection, AcademicTerm.code).join(AcademicTerm)
    if term:
        query = query.where(AcademicTerm.code == term)
    result = []
    for section, term_code in db.execute(query.order_by(AcademicTerm.code, TimetableSection.code)):
        result.append({"term_code": term_code, "code": section.code, "name": section.name,
                       "division_code": section.division_code, "provenance": section.provenance})
    return result


@router.get("/sections/{section_code}/timetable")
def section_timetable(section_code: str, term: str, day: str | None = None, batch: str | None = None,
                      db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "maintenance":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Maintenance cannot read section timetables")
    academic_term = _term(db, term)
    section = _section(db, academic_term.id, section_code)
    if user.role == "student":
        student = db.scalar(select(Student).where(Student.usn == user.username))
        mapping = db.scalar(select(DivisionSectionMap).where(DivisionSectionMap.division_code == student.division_code)) if student else None
        own_letter = mapping.section_letter if mapping else None
        if not student or academic_term.code != ACTIVE_TERM or section.code != own_letter:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Students may read only their mapped section")
    query = select(TimetableSession).where(TimetableSession.term_id == academic_term.id,
                                           TimetableSession.section_id == section.id)
    if day:
        query = query.where(TimetableSession.day == day)
    if batch:
        query = query.where(TimetableSession.batch.in_(("ALL", batch)))
    rows = list(db.scalars(query.order_by(TimetableSession.day, TimetableSession.start_period,
                                          TimetableSession.batch)))
    return [_session_out(db, row) for row in rows]


@router.get("/students/me")
def student_me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "student":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Student account required")
    student = db.scalar(select(Student).where(Student.usn == user.username))
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Roster student not found")
    mapping = db.scalar(select(DivisionSectionMap).where(DivisionSectionMap.division_code == student.division_code))
    return {"usn": student.usn, "full_name": student.full_name, "division_code": student.division_code,
            "section_code": mapping.section_letter if mapping else None, "lab_batch": student.lab_batch,
            "provenance": student.provenance, "mapping_data_status": mapping.data_status if mapping else None}


@router.get("/timetable/student/me")
def student_timetable(term: str | None = None, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    if user.role != "student":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Student account required")
    student = db.scalar(select(Student).where(Student.usn == user.username))
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Roster student not found")
    mapping = db.scalar(select(DivisionSectionMap).where(DivisionSectionMap.division_code == student.division_code))
    if mapping is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Student division has no section mapping")
    academic_term = _term(db, term)
    if academic_term.code != ACTIVE_TERM:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No student division mapping for term")
    section = _section(db, academic_term.id, mapping.section_letter)
    batch = "B1" if student.lab_batch == "A1" else "B2" if student.lab_batch == "A2" else None
    query = select(TimetableSession).where(TimetableSession.term_id == academic_term.id,
                                           TimetableSession.section_id == section.id)
    if batch:
        query = query.where(TimetableSession.batch.in_(("ALL", batch)))
    rows = list(db.scalars(query.order_by(TimetableSession.day, TimetableSession.start_period)))
    return {"usn": student.usn, "term_code": academic_term.code,
            "division_code": student.division_code, "section_code": section.code,
            "lab_batch": student.lab_batch, "sessions": [_session_out(db, row) for row in rows]}


@router.get("/timetable/faculty/{faculty_id}")
def faculty_timetable(faculty_id: int, term: str, day: str | None = None,
                      db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in {"admin", "hod", "teaching_faculty"}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Faculty timetable access denied")
    academic_term = _term(db, term)
    faculty = db.get(Faculty, faculty_id)
    if faculty is None or faculty.term_id != academic_term.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Faculty record not found in term")
    if user.role != "admin" and user.username.upper() != faculty.initials:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Faculty may read only their own timetable")
    query = (select(TimetableSession).join(TimetableSessionFaculty)
             .where(TimetableSessionFaculty.faculty_id == faculty.id,
                    TimetableSession.term_id == academic_term.id))
    if day:
        query = query.where(TimetableSession.day == day)
    rows = list(db.scalars(query.order_by(TimetableSession.day, TimetableSession.start_period)))
    return {"faculty_id": faculty.id, "term_code": academic_term.code,
            "initials": faculty.initials, "name": faculty.full_name,
            "sessions": [_session_out(db, row) for row in rows]}


@router.get("/rooms/{room_id}/timetable")
def room_timetable(room_id: str, term: str, day: str | None = None,
                   db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    canonical = resolve_room(room_id)
    room = db.scalar(select(Room).where(Room.number == canonical)) if canonical else None
    if room is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
    academic_term = _term(db, term)
    query = select(TimetableSession).where(TimetableSession.term_id == academic_term.id,
                                           TimetableSession.room_id == room.id)
    if day:
        query = query.where(TimetableSession.day == day)
    rows = list(db.scalars(query.order_by(TimetableSession.day, TimetableSession.start_period)))
    return {"room_id": room.number, "term_code": academic_term.code,
            "sessions": [_session_out(db, row) for row in rows]}


@router.get("/rooms/availability")
def room_availability(day: str, period: int = Query(ge=1, le=7), term: str | None = None,
                      db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    if day not in DAYS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "day must be Mon through Sat")
    academic_term = _term(db, term)
    rooms = list(db.scalars(select(Room).order_by(Room.floor, Room.number)))
    sessions = list(db.scalars(select(TimetableSession).where(TimetableSession.term_id == academic_term.id,
                                                              TimetableSession.day == day,
                                                              TimetableSession.start_period <= period,
                                                              TimetableSession.end_period >= period)))
    occupied: dict[int, list[int]] = {}
    for session_row in sessions:
        if session_row.room_id is not None and session_row.room_required:
            occupied.setdefault(session_row.room_id, []).append(session_row.id)
    response_rooms = []
    for room in rooms:
        row = {"room_id": room.number, "available": room.id not in occupied,
               "provenance": room.provenance}
        if room.id in occupied:
            row["session_ids"] = occupied[room.id]
        response_rooms.append(row)
    return {"day": day, "period": period, "term_code": academic_term.code, "rooms": response_rooms}


@router.get("/timetable/conflicts")
def timetable_conflicts(term: str, db: Session = Depends(get_db),
                        _user: User = Depends(require_roles("admin", "hod"))):
    academic_term = _term(db, term)
    conflicts = _db_conflicts(db, academic_term.id)
    return {"term_code": academic_term.code, "conflicts": conflicts}


@router.post("/timetable/sessions", status_code=status.HTTP_201_CREATED)
def create_session(body: TimetableSessionCreate, db: Session = Depends(get_db),
                   _admin: User = Depends(require_roles("admin"))):
    academic_term = _term(db, body.term_code)
    section, subject, faculty, room = _validated_session_refs(
        db, academic_term, body.section_code, body.subject_code, body.faculty_id, body.room_id)
    _validate_times(body.day, body.periods, body.batch, body.room_required, room.number if room else None)
    candidate = {"term_code": academic_term.code, "section_code": section.code, "batch": body.batch,
                 "day": body.day, "start_period": min(body.periods), "end_period": max(body.periods),
                 "faculty_initials": [faculty.initials] if faculty else [], "room_id": room.number if room else None,
                 "room_required": body.room_required, "block_id": body.block_id}
    conflict = _write_conflict_for(candidate, _session_inputs(db, academic_term.id))
    if conflict:
        raise HTTPException(status.HTTP_409_CONFLICT, {"detail": "session clashes", "conflict": conflict})
    row = TimetableSession(term_id=academic_term.id, section_id=section.id, batch=body.batch,
                           day=body.day, start_period=min(body.periods), end_period=max(body.periods),
                           subject_id=subject.id, faculty_id=faculty.id if faculty else None,
                           room_id=room.id if room else None, room_required=body.room_required,
                           raw_label=body.raw_label, block_id=body.block_id,
                           provenance="SYNTHETIC", version=1)
    db.add(row)
    db.flush()
    if faculty:
        db.add(TimetableSessionFaculty(session_id=row.id, faculty_id=faculty.id, provenance="SYNTHETIC"))
    db.commit()
    db.refresh(row)
    return _session_out(db, row)


@router.patch("/timetable/sessions/{session_id}")
def update_session(session_id: int, body: TimetableSessionPatch, db: Session = Depends(get_db),
                   _admin: User = Depends(require_roles("admin"))):
    row = db.get(TimetableSession, session_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    changes = body.model_dump(exclude_unset=True)
    expected_version = changes.pop("expected_version")
    if expected_version != row.version:
        raise HTTPException(status.HTTP_409_CONFLICT, {"detail": "version conflict", "version": row.version})
    term = db.get(AcademicTerm, row.term_id)
    section = db.get(TimetableSection, row.section_id)
    subject = db.get(TimetableSubject, row.subject_id) if row.subject_id else None
    faculty = db.get(Faculty, row.faculty_id) if row.faculty_id else None
    room = db.get(Room, row.room_id) if row.room_id else None
    mapped = {"section_code": section.code, "subject_code": subject.code if subject else None,
              "faculty_id": faculty.id if faculty else None, "room_id": room.number if room else None,
              "day": row.day, "periods": list(range(row.start_period, row.end_period + 1)),
              "batch": row.batch, "room_required": row.room_required, "raw_label": row.raw_label,
              "block_id": row.block_id}
    mapped.update(changes)
    new_section, new_subject, new_faculty, new_room = _validated_session_refs(
        db, term, mapped["section_code"], mapped["subject_code"], mapped["faculty_id"], mapped["room_id"])
    _validate_times(mapped["day"], mapped["periods"], mapped["batch"], mapped["room_required"],
                    new_room.number if new_room else None)
    candidate = {"term_code": term.code, "section_code": new_section.code, "batch": mapped["batch"],
                 "day": mapped["day"], "start_period": min(mapped["periods"]), "end_period": max(mapped["periods"]),
                 "faculty_initials": [new_faculty.initials] if new_faculty else [],
                 "room_id": new_room.number if new_room else None,
                 "room_required": mapped["room_required"], "block_id": mapped["block_id"]}
    conflict = _write_conflict_for(candidate, _session_inputs(db, term.id, exclude_id=row.id))
    if conflict:
        raise HTTPException(status.HTTP_409_CONFLICT, {"detail": "session clashes", "conflict": conflict})
    row.section_id, row.subject_id = new_section.id, new_subject.id
    row.faculty_id = new_faculty.id if new_faculty else None
    row.room_id = new_room.id if new_room else None
    row.day, row.batch = mapped["day"], mapped["batch"]
    row.start_period, row.end_period = min(mapped["periods"]), max(mapped["periods"])
    row.room_required, row.raw_label, row.block_id = mapped["room_required"], mapped["raw_label"], mapped["block_id"]
    if "room_id" in changes:
        row.room_inferred = False
    row.provenance = "SYNTHETIC"
    row.version += 1
    db.query(TimetableSessionFaculty).filter(TimetableSessionFaculty.session_id == row.id).delete()
    if new_faculty:
        db.add(TimetableSessionFaculty(session_id=row.id, faculty_id=new_faculty.id, provenance="SYNTHETIC"))
    db.commit()
    db.refresh(row)
    return _session_out(db, row)


@router.get("/meta/data-status")
def data_status(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    terms = list(db.scalars(select(AcademicTerm).order_by(AcademicTerm.code)))
    session_rows = list(db.scalars(select(TimetableSession)))
    terms_out = []
    for term in terms:
        count = sum(row.term_id == term.id for row in session_rows)
        terms_out.append({"code": term.code, "provenance": term.provenance, "session_count": count})
    inferred_rooms = {row.room_id for row in session_rows if row.provenance == "INFERRED" and row.room_id}
    conflict_counts = Counter()
    for term in terms:
        conflict_counts.update(conflict["type"] for conflict in _db_conflicts(db, term.id))
    return {"terms": terms_out, "counts": {
        "subjects": db.query(TimetableSubject).count(), "faculty": db.query(Faculty).count(),
        "sections": db.query(TimetableSection).count(), "sessions": len(session_rows),
        "inferred_rooms": len(inferred_rooms),
        "roomless_sessions": sum(not row.room_required for row in session_rows),
    }, "conflicts": {key: conflict_counts[key] for key in ("room", "faculty", "section")}}


@router.get("/timetable/date/{date_value}")
def timetable_by_date(date_value: Date, term: str | None = None, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    academic_term = _term(db, term)
    weekday = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[date_value.weekday()]
    holiday = db.scalar(select(Holiday).where(Holiday.holiday_date == date_value))
    if holiday or weekday == "Sun":
        return {"date": date_value.isoformat(), "weekday": weekday,
                "holiday": holiday.name if holiday else None, "sessions": []}
    rows = list(db.scalars(select(TimetableSession).where(TimetableSession.term_id == academic_term.id,
                                                          TimetableSession.day == weekday)
                            .order_by(TimetableSession.start_period)))
    sessions = [] if user.role == "maintenance" else [_session_out(db, row) for row in rows]
    return {"date": date_value.isoformat(), "weekday": weekday, "holiday": None, "sessions": sessions}
