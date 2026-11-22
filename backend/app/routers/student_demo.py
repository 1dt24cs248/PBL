from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import (AcademicTerm, DivisionSectionMap, Faculty, Holiday, Room, Section, Student,
                      TimetableSection, TimetableSession, TimetableSessionFaculty, TimetableSubject, User)

router = APIRouter(prefix="/students/me", tags=["synthetic-student-demo"])
ACTIVE_TERM = "2026-27-ODD"
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
ALT_CODES = {"BCS515B": "BCS504B", "BCS506": "BCS505", "B**K507": "BCV508"}


def _today() -> date:
    """Clock seam for deterministic date-window tests."""
    return date.today()


def _student_context(db: Session, user: User):
    if user.role != "student":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Student account required")
    student = db.scalar(select(Student).where(Student.usn == user.username))
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Roster student not found")
    mapping = db.scalar(select(DivisionSectionMap).where(
        DivisionSectionMap.division_code == student.division_code
    ))
    if mapping is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Student division has no section mapping")
    term = db.scalar(select(AcademicTerm).where(AcademicTerm.code == ACTIVE_TERM))
    section = db.scalar(select(TimetableSection).where(
        TimetableSection.term_id == term.id, TimetableSection.code == mapping.section_letter
    )) if term else None
    if term is None or section is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student timetable is not available")
    query = select(TimetableSession).where(
        TimetableSession.term_id == term.id, TimetableSession.section_id == section.id
    )
    if student.lab_batch == "A1":
        query = query.where(TimetableSession.batch.in_(("ALL", "B1")))
    elif student.lab_batch == "A2":
        query = query.where(TimetableSession.batch.in_(("ALL", "B2")))
    else:
        query = query.where(TimetableSession.batch == "ALL")
    rows = list(db.scalars(query.order_by(TimetableSession.day, TimetableSession.start_period,
                                          TimetableSession.batch)))
    return student, mapping, term, section, rows


def _subject(db: Session, row: TimetableSession) -> TimetableSubject | None:
    return db.get(TimetableSubject, row.subject_id) if row.subject_id else None


def _component(code: str, name: str) -> str:
    return "Practical" if code.upper().startswith("BCSL") or " LAB" in name.upper() else "Theory"


def _slot_key(row: TimetableSession, subject: TimetableSubject | None) -> str:
    return row.block_id or f"{subject.code if subject else 'unknown'}|{row.day}|{row.start_period}|{row.end_period}|{row.batch}"


def _unit_hash(value: str) -> float:
    number = int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:16], 16)
    return number / float(16 ** 16)


def _attendance_status(usn: str, day: date, slot_key: str, subject_code: str) -> str:
    value = _unit_hash(f"{usn}|{day.isoformat()}|{slot_key}|{settings.demo_salt}")
    if value < 0.03:
        return "NA"
    normalized = (value - 0.03) / 0.97
    probability = 0.72 + 0.24 * _unit_hash(f"{usn}|{subject_code}")
    return "P" if normalized < probability else "A"


def _attendance_grid(db: Session, user: User, start: date | None, end: date | None) -> list[dict]:
    student, _mapping, _term, _section, sessions = _student_context(db, user)
    today, yesterday = _today(), _today() - timedelta(days=1)
    first = start or settings.demo_attendance_start
    last = min(end or yesterday, yesterday)
    if first > last:
        return []
    holidays = set(db.scalars(select(Holiday.holiday_date).where(
        Holiday.holiday_date >= first, Holiday.holiday_date <= last
    )))
    by_day: dict[str, list[TimetableSession]] = defaultdict(list)
    for row in sessions:
        by_day[row.day].append(row)
    output = []
    current = first
    while current <= last:
        weekday = WEEKDAYS[current.weekday()]
        if weekday == "Sun":
            current += timedelta(days=1)
            continue
        slot_rows = []
        if current not in holidays:
            for row in by_day.get(weekday, []):
                subject = _subject(db, row)
                slot = f"P{row.start_period}" if row.start_period == row.end_period else f"P{row.start_period}-P{row.end_period}"
                slot_rows.append({
                    "slot": slot,
                    "subject_code": subject.code if subject else None,
                    "subject_name": subject.name if subject else None,
                    "status": _attendance_status(student.usn, current, _slot_key(row, subject), subject.code if subject else "unknown"),
                })
        if not slot_rows:
            slot_rows = [{"slot": None, "subject_code": None, "subject_name": None, "status": "-"}]
        output.append({"date": current.isoformat(), "weekday": weekday, "slots": slot_rows})
        current += timedelta(days=1)
    output.reverse()
    return output


@router.get("/profile")
def student_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    student, mapping, _term, _section, _sessions = _student_context(db, user)
    division_section = db.scalar(select(Section).where(Section.code == student.division_code))
    room = db.get(Room, division_section.home_room_id) if division_section else None
    letter = mapping.section_letter
    return {
        "usn": student.usn, "full_name": student.full_name, "branch": "CS", "department": "CSE",
        "semester": 5, "division": student.division_code,
        "section_label": f"CS-5-{letter}", "section_mapping_status": mapping.data_status,
        "lab_batch": student.lab_batch, "roll_no": None,
        "home_room": {"code": room.number, "real_label": room.real_label} if room else None,
        "data_status": "SYNTHETIC",
    }


@router.get("/attendance")
def student_attendance(from_date: date | None = Query(None, alias="from"),
                       to_date: date | None = Query(None, alias="to"),
                       db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "from must be on or before to")
    return {"data_status": "SYNTHETIC", "days": _attendance_grid(db, user, from_date, to_date)}


@router.get("/attendance/summary")
def student_attendance_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    grid = _attendance_grid(db, user, None, None)
    overall = {"present": 0, "absent": 0, "no_attendance": 0, "total": 0}
    by_subject: dict[str, dict] = {}
    for day in grid:
        for slot in day["slots"]:
            status_code = slot["status"]
            if status_code not in {"P", "A", "NA"}:
                continue
            overall["total"] += 1
            overall[{"P": "present", "A": "absent", "NA": "no_attendance"}[status_code]] += 1
            code = slot["subject_code"]
            item = by_subject.setdefault(code, {"subject_code": code, "subject_name": slot["subject_name"],
                                                "component": _component(code, slot["subject_name"]),
                                                "total": 0, "present": 0, "absent": 0})
            item["total"] += 1
            if status_code == "P":
                item["present"] += 1
            elif status_code == "A":
                item["absent"] += 1
    denominator = overall["present"] + overall["absent"]
    overall["percent"] = round(overall["present"] / denominator * 100, 2) if denominator else 0.0
    subjects = []
    for item in sorted(by_subject.values(), key=lambda row: row["subject_code"]):
        denominator = item["present"] + item["absent"]
        percent = round(item["present"] / denominator * 100, 2) if denominator else 0.0
        subjects.append({key: item[key] for key in ("subject_code", "subject_name", "component", "total", "present")}
                        | {"percent": percent, "status": "low" if percent < 75 else "ok"})
    return {"data_status": "SYNTHETIC", "overall": overall, "subjects": subjects}


@router.get("/lms/subjects")
def student_lms_subjects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _student, _mapping, _term, _section, sessions = _student_context(db, user)
    subjects_by_id = {}
    for row in sessions:
        subject = _subject(db, row)
        if subject and not subject.code.startswith("ACT-"):
            subjects_by_id[subject.id] = subject
    result = []
    for subject in sorted(subjects_by_id.values(), key=lambda item: item.code):
        faculty_ids = db.scalars(select(TimetableSessionFaculty.faculty_id)
                                 .join(TimetableSession, TimetableSession.id == TimetableSessionFaculty.session_id)
                                 .where(TimetableSession.subject_id == subject.id,
                                        TimetableSession.section_id == _section.id)).all()
        names = sorted({name for faculty_id in faculty_ids
                        if (faculty := db.get(Faculty, faculty_id)) is not None
                        if (name := faculty.full_name)})
        result.append({"subject_code": subject.code, "alt_code": ALT_CODES.get(subject.code),
                       "subject_name": subject.name,
                       "component": _component(subject.code, subject.name),
                       "semester": 5, "faculty_names": names})
    return {"data_status": "SYNTHETIC", "subjects": result}


@router.get("/fees")
def student_fees(_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Validate ownership/role even though the fictional ledger has no stored rows.
    _student_context(db, _user)
    heads = [
        {"name": "Tuition", "amount": settings.demo_fee_tuition_per_year},
        {"name": "Academic", "amount": settings.demo_fee_academic_per_year},
        {"name": "Examination", "amount": settings.demo_fee_examination_per_year},
        {"name": "University", "amount": settings.demo_fee_university_per_year},
        {"name": "Skill Lab", "amount": settings.demo_fee_skill_lab_per_year},
    ]
    total = sum(item["amount"] for item in heads)
    years = []
    for year in range(1, 4):
        receipts = []
        if year <= 2:
            receipts = [{"receipt_no": f"SYN-{year:04d}", "date": f"{2023 + year}-06-01",
                         "heads": heads, "mode": "SYNTHETIC"}]
        years.append({"year": year, "total": total, "receipts": receipts})
    paid = total * 2
    due = total * 3
    return {"data_status": "SYNTHETIC",
            "ledger": {"to_be_collected": due, "paid": paid, "previous": 0, "pending": due - paid},
            "years": years,
            "scholarship": {"status": "Not applicable", "note": "Synthetic demo"}}
