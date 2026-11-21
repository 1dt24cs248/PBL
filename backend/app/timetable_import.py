"""Code-based parser/importer for the three timetable datasets in the spec."""
from __future__ import annotations

import re
import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .dataset import SPEC_PATH
from .models import (
    AcademicTerm, Faculty, Room, TimetableSection, TimetableSession,
    TimetableSessionFaculty, TimetableSubject,
)
from .room_resolver import resolve_room


TERM_SPECS = (
    ("2026-27-ODD", 5, "ODD", "Dataset 1:", "Dataset 2:"),
    ("2025-26-ODD", 3, "ODD", "Dataset 2:", "Dataset 3:"),
    ("2024-25-EVEN", 2, "EVEN", "Dataset 3:", "Complete Official DSATM CSE Student Roster"),
)
DAY_RE = re.compile(r"\b(Mon|Tue|Wed|Thu|Fri|Sat)\b\s*:?\s*(?=P\d)", re.I)
PERIOD_RE = re.compile(r"\bP(\d{1,2})(?:\s*[-–]\s*P?(\d{1,2}))?\b", re.I)
ROOM_AT_RE = re.compile(r"@\s*([^()]*?)(?=\s*/\s*B[12]:|\)|$)", re.I)
ROOMLESS_MARKERS = ("NPTEL/MOOC", "PRE-PLACEMENT", "NSS/YOGA", "SKILL DEV")
WEEKDAYS = {"mon": "Mon", "tue": "Tue", "wed": "Wed", "thu": "Thu", "fri": "Fri", "sat": "Sat"}


@dataclass
class ParsedTimetables:
    terms: list[dict]
    subjects: list[dict]
    faculty: list[dict]
    sections: list[dict]
    sessions: list[dict]
    inferred_rooms: set[str]
    conflicts: list[dict]
    parse_issues: list[str]
    excluded_b_block_labs: int


def parse_timetables(path: Path = SPEC_PATH) -> ParsedTimetables:
    text = path.read_text(encoding="utf-8")
    all_terms, all_subjects, all_faculty, all_sections, all_sessions = [], [], [], [], []
    inferred_rooms: set[str] = set()
    issues: list[str] = []
    excluded_b_block_labs = 0
    for code, semester, kind, start, end in TERM_SPECS:
        start_ix = text.index(start)
        end_ix = text.index(end, start_ix + len(start))
        source = text[start_ix:end_ix]
        catalog = _subject_catalog(source, code)
        if code == "2024-25-EVEN":
            issues.append("2024-25-EVEN has no subject-code catalogue in the source text; source abbreviations are retained as subject codes and marked INFERRED.")
        section_chunks = _section_chunks(source, code)
        term = {"code": code, "academic_year": code.split("-")[0] + "-" + code.split("-")[1],
                "semester": semester, "term_kind": kind, "provenance": "REAL_DSATM_PDF"}
        all_terms.append(term)
        term_subjects: dict[str, dict] = {subject["code"]: subject for subject in catalog.values()}
        term_faculty: dict[str, dict] = {}
        term_sections: list[dict] = []
        term_sessions: list[dict] = []
        for section_code, section_name, header, body in section_chunks:
            home_room = _header_room(header)
            division = None
            if code == "2026-27-ODD":
                division = f"CSE-{ord(section_code) - ord('A') + 1}"
            section = {"term_code": code, "code": section_code, "name": section_name,
                       "division_code": division, "home_room_id": home_room,
                       "provenance": "REAL_DSATM_PDF"}
            term_sections.append(section)
            section_subject_faculty: dict[str, str] = {}
            if code == "2026-27-ODD":
                for initials, full_name, subject_labels in _faculty_declarations(body):
                    _remember_faculty(term_faculty, initials, full_name, "REAL_DSATM_PDF")
                    for subject_label in subject_labels:
                        section_subject_faculty[subject_label] = initials
            for day, day_text in _split_days(body):
                blocks = list(PERIOD_RE.finditer(day_text))
                for block_ix, period_match in enumerate(blocks):
                    start_period = int(period_match.group(1))
                    end_period = int(period_match.group(2) or start_period)
                    next_ix = blocks[block_ix + 1].start() if block_ix + 1 < len(blocks) else len(day_text)
                    label = day_text[period_match.end():next_ix].strip(" .;,\r\n\t")
                    if not label:
                        continue
                    start_mark = f"P{start_period}" if start_period == end_period else f"P{start_period}-P{end_period}"
                    raw_label = f"{day} {start_mark} {label}"[:500]
                    if re.search(r"\bB-[12]\b", label.upper()) and "LAB" in label.upper():
                        excluded_b_block_labs += 1
                        continue
                    generated = _make_sessions(
                        code, section_code, day, start_period, end_period, label,
                        raw_label, home_room, catalog,
                    )
                    for item in generated:
                        faculty_inferred = False
                        if not item["faculty_initials"]:
                            abbreviation = _find_subject_abbreviation(label, catalog)
                            inherited_initials = section_subject_faculty.get(abbreviation or "")
                            if inherited_initials:
                                item["faculty_initials"] = [inherited_initials]
                                faculty_inferred = True
                        for initials in item["faculty_initials"]:
                            _remember_faculty(term_faculty, initials, None, "REAL_DSATM_PDF")
                        if item["subject_code"]:
                            subject = next((value for value in catalog.values()
                                            if value["code"] == item["subject_code"]), None)
                            if subject is None:
                                subject = {"code": item["subject_code"], "name": item["subject_name"],
                                           "provenance": item["provenance"]}
                            term_subjects[subject["code"]] = subject
                            item["subject_name"] = subject["name"]
                        item.update({"term_code": code, "section_code": section_code, "day": day,
                                     "start_period": start_period, "end_period": end_period,
                                     "raw_label": raw_label})
                        if faculty_inferred and item["provenance"] == "REAL_DSATM_PDF":
                            item["provenance"] = "INFERRED"
                        if item["room_id"] and item.get("room_inferred", False):
                            inferred_rooms.add(item["room_id"])
                        term_sessions.append(item)
        all_subjects.extend({"term_code": code, **value} for value in term_subjects.values())
        all_faculty.extend({"term_code": code, **value} for value in term_faculty.values())
        all_sections.extend(term_sections)
        all_sessions.extend(term_sessions)
    conflicts = detect_conflicts(all_sessions)
    return ParsedTimetables(all_terms, all_subjects, all_faculty, all_sections,
                            all_sessions, inferred_rooms, conflicts, issues, excluded_b_block_labs)


def _subject_catalog(source: str, term_code: str) -> dict[str, dict]:
    catalog = {}
    section_start = source.find("Subjects:")
    if section_start < 0:
        return catalog
    line_end = source.find("\n", section_start)
    shared_labs = source.find("Shared Labs:", section_start)
    if shared_labs >= 0 and (line_end < 0 or shared_labs < line_end):
        line_end = shared_labs
    line = source[section_start:line_end if line_end >= 0 else len(source)].removeprefix("Subjects:").strip()
    entries = re.split(r",\s*(?=[A-Z0-9*]+\s)", line)
    for entry in entries:
        entry = entry.strip().rstrip(".")
        if term_code == "2025-26-ODD":
            item = re.fullmatch(r"\s*([A-Z0-9*]+)\s+\(([A-Z0-9/+& -]+)\)\s*", entry)
            if item:
                code, abbreviation = item.groups()
                catalog[abbreviation.upper()] = {"code": code, "name": abbreviation,
                                                 "provenance": "REAL_DSATM_PDF"}
        else:
            item = re.fullmatch(r"\s*([A-Z0-9*]+)\s+(.+?)\s+\(([^()]+)\)\s*", entry)
            if item:
                code, name, abbreviation = item.groups()
                catalog[abbreviation.upper()] = {"code": code, "name": name.strip(),
                                                 "provenance": "REAL_DSATM_PDF"}
    final_subject = re.search(r"\b([A-Z0-9*]+)\s+(NSS/PE/Yoga)\.?$", line, re.I)
    if final_subject:
        code, name = final_subject.groups()
        catalog[name.upper()] = {"code": code, "name": name, "provenance": "REAL_DSATM_PDF"}
    return catalog


def _section_chunks(source: str, term_code: str) -> list[tuple[str, str, str, str]]:
    if term_code == "2026-27-ODD":
        pattern = re.compile(r"(?m)^5TH ([A-F]) SECTION \| ([^\n]+)")
        matches = list(pattern.finditer(source))
        return [(m.group(1), f"5th {m.group(1)}", m.group(2),
                 source[m.end():matches[i + 1].start() if i + 1 < len(matches) else len(source)])
                for i, m in enumerate(matches)]
    if term_code == "2025-26-ODD":
        pattern = re.compile(r"(?m)^3rd ([A-F]) \(([^\n]+?)\):")
        matches = list(pattern.finditer(source))
        chunks = []
        for i, match in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
            header = match.group(2)
            chunks.append((match.group(1), f"3rd {match.group(1)}", header, source[match.end():end]))
        return chunks
    pattern = re.compile(r"(?m)^(CSE-\d+|CS-ICB|CS-DS) \(([^\n]+?)\):")
    matches = list(pattern.finditer(source))
    chunks = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        chunks.append((match.group(1), match.group(1), match.group(2), source[match.end():end]))
    return chunks


def _header_room(header: str) -> str | None:
    canonical = re.search(r"A-F[1-5]-\d{2}|A-G\d{2}|A-B\d{2}", header)
    if canonical:
        return canonical.group(0)
    prefixed = re.search(r"A[- ]\d{3}", header, re.I)
    if prefixed and resolve_room(prefixed.group(0)):
        return resolve_room(prefixed.group(0))
    return resolve_room(header)


def _faculty_declarations(body: str) -> list[tuple[str, str, list[str]]]:
    line_match = re.search(r"(?m)^Faculty:\s*(.*)$", body)
    if not line_match:
        return []
    line = line_match.group(1)
    declarations = []
    for match in re.finditer(r"\b([A-Z]{2,4})\s+(.+?)\s+\(([A-Z0-9, /&+-]+)\)(?=,|\.|$)", line):
        initials, name, subjects = match.groups()
        declarations.append((initials, name.strip(), [item.strip() for item in subjects.split(",")]))
    return declarations


def _remember_faculty(faculty: dict[str, dict], initials: str, name: str | None, provenance: str) -> None:
    if not re.fullmatch(r"[A-Z]{2,4}", initials):
        return
    current = faculty.get(initials)
    if current is None:
        faculty[initials] = {"initials": initials, "full_name": name, "provenance": provenance if name else "REAL_DSATM_PDF"}
    elif name and current["full_name"] not in (None, name):
        current["full_name"] = None
        current["provenance"] = "INFERRED"
    elif name:
        current["full_name"] = name


def _split_days(body: str) -> list[tuple[str, str]]:
    matches = list(DAY_RE.finditer(body))
    return [(WEEKDAYS[m.group(1).lower()], body[m.end():matches[i + 1].start() if i + 1 < len(matches) else len(body)])
            for i, m in enumerate(matches)]


def _make_sessions(term_code: str, section_code: str, day: str, start: int, end: int,
                   label: str, raw_label: str, home_room: str | None,
                   catalog: dict[str, dict]) -> list[dict]:
    upper = label.upper()
    digest = hashlib.sha1(raw_label.encode("utf-8")).hexdigest()[:8]
    block_id = f"{term_code}-{section_code}-{day.upper()}-P{start}-P{end}-{digest}"
    if any(marker in upper for marker in ROOMLESS_MARKERS):
        activity = next((marker for marker in ROOMLESS_MARKERS if marker in upper), "ACTIVITY")
        if activity == "NSS/YOGA" and "NSS/PE/YOGA" in catalog:
            activity_subject = catalog["NSS/PE/YOGA"]
            code, name = activity_subject["code"], activity_subject["name"]
        else:
            code = f"ACT-{re.sub(r'[^A-Z0-9]+', '-', activity).strip('-')}"
            name = activity
            catalog.setdefault(code, {"code": code, "name": name, "provenance": "INFERRED"})
        return [{"batch": "ALL", "subject_code": code, "subject_name": name, "faculty_initials": [],
                 "room_id": None, "room_required": False,
                 "block_id": block_id, "provenance": "REAL_DSATM_PDF", "room_inferred": False}]

    # Source rows can list B1 or B2 first. Parse both branch markers in source
    # order instead of assuming B1 precedes B2 (5C Thu lists B2 first).
    branches = re.findall(
        r"\b(B[12]):\s*(.*?)(?=\s*/\s*B[12]:|\)|$)", label, re.I
    )
    if len(branches) == 2 and {batch.upper() for batch, _ in branches} == {"B1", "B2"}:
        made = []
        for batch, branch in branches:
            batch = batch.upper()
            room_match = ROOM_AT_RE.search(branch)
            room_id = resolve_room(room_match.group(1)) if room_match else None
            inferred = False
            if room_id is None:
                room_id = _parallel_room(term_code, label, batch)
                inferred = bool(room_id)
            subject_code, subject_name = _parallel_subject(term_code, label, room_id, catalog)
            initials = re.findall(r"[A-Z]{2,4}", branch.split("@")[0])
            made.append({"batch": batch, "subject_code": subject_code, "subject_name": subject_name,
                         "faculty_initials": initials,
                         "room_id": room_id, "room_required": True,
                         "block_id": block_id, "provenance": "INFERRED" if inferred else "REAL_DSATM_PDF",
                         "room_inferred": inferred})
        return made

    room_match = ROOM_AT_RE.search(label)
    room_id = resolve_room(room_match.group(1)) if room_match else None
    inferred = False
    if room_id is None:
        room_id = _shared_lab_room(term_code, section_code, label) or home_room
        inferred = bool(room_id)
    room_required = True
    abbrev = _find_subject_abbreviation(label, catalog)
    subject = catalog.get(abbrev) if abbrev else None
    if subject is None:
        simple = re.sub(r"\([^)]*\)", "", label)
        simple = re.sub(r"@.*", "", simple).strip(" /.,;")
        subject_code = re.sub(r"[^A-Z0-9+*/&-]+", "-", simple.upper()).strip("-") or "UNKNOWN"
        subject_name = simple or subject_code
        provenance = "INFERRED"
    else:
        subject_code, subject_name, provenance = subject["code"], subject["name"], subject["provenance"]
    initials = _initials(label)
    return [{"batch": "ALL", "subject_code": subject_code, "subject_name": subject_name,
             "faculty_initials": initials,
             "room_id": room_id, "room_required": room_required, "block_id": block_id,
             "provenance": "INFERRED" if inferred or provenance == "INFERRED" else "REAL_DSATM_PDF",
             "room_inferred": inferred}]


def _initials(text: str) -> list[str]:
    values = []
    for contents in re.findall(r"\(([A-Z]{2,4}(?:\s*,\s*[A-Z]{2,4})*)\)", text):
        values.extend(re.findall(r"[A-Z]{2,4}", contents))
    # Branch syntax has initials outside parentheses.
    if re.search(r"B[12]:", text, re.I):
        before_room = text.split("@")[0]
        values.extend(re.findall(r"\b[A-Z]{2,4}\b", before_room))
    ignored = {"B1", "B2", "LAB", "NEXT", "GEN", "CG", "PYT", "DDCO"}
    return list(dict.fromkeys(value for value in values if value not in ignored))


def _find_subject_abbreviation(label: str, catalog: dict[str, dict]) -> str | None:
    upper = label.upper()
    aliases = {
        "NEX-GEN LAB": ("NEX-GEN LAB",), "ML LAB": ("ML",), "DS LAB": ("DS",),
        "JAVA LAB": ("JAVA",), "DDCO/PYT": ("DDCO",), "CAED LAB": ("CAED",),
        "CAED THEORY": ("CAED",), "C++": ("C++",), "PRE-PLACEMENT": ("PRE-PLACEMENT",),
        "EVS": ("EVS/EVEW",), "NSS/YOGA": ("NSS/PE/YOGA",),
    }
    for marker, mapped in aliases.items():
        if marker in upper:
            for abbreviation in mapped:
                if abbreviation in catalog:
                    return abbreviation
    candidates = sorted(catalog.keys(), key=len, reverse=True)
    for abbreviation in candidates:
        if re.search(rf"(?<![A-Z0-9]){re.escape(abbreviation)}(?![A-Z0-9])", upper):
            return abbreviation
    # Term-3/2 labels without a supplied catalogue remain source abbreviations.
    first = re.match(r"\s*([A-Z][A-Z0-9+/-]*)", upper)
    return first.group(1) if first else None


def _parallel_room(term_code: str, label: str, batch: str) -> str | None:
    upper = label.upper()
    if "CG LAB" in upper or "NEXT GEN LAB" in upper:
        return "A-F2-10" if batch == "B1" else "A-F2-06"
    if "DDCO/PYT" in upper:
        return "A-F2-06" if batch == "B1" else "A-F2-10"
    return None


def _parallel_subject(term_code: str, label: str, room_id: str | None,
                      catalog: dict[str, dict]) -> tuple[str, str]:
    upper = label.upper()
    if "CG LAB" in upper or "NEXT GEN LAB" in upper:
        if room_id == "A-F2-06":
            subj = catalog.get("NEX-GEN LAB", {"code": "BCSL504", "name": "Next Generation Embedded Lab"})
        else:
            subj = catalog.get("FCG", {"code": "BCS501", "name": "Fundamentals of Computer Graphics"})
        return subj["code"], subj["name"]
    if "DDCO/PYT" in upper:
        abbreviation = "DDCO" if room_id == "A-F2-06" else "PYT LAB"
        subj = catalog.get(abbreviation, {"code": abbreviation, "name": abbreviation})
        return subj["code"], subj["name"]
    return "LAB", "Lab"


def _shared_lab_room(term_code: str, section_code: str, label: str) -> str | None:
    upper = label.upper()
    if term_code == "2026-27-ODD":
        if "ML LAB" in upper:
            return "A-F5-06" if section_code == "C" else "A-F3-05"
        if "DS LAB" in upper:
            return "A-F3-05"
    if term_code == "2025-26-ODD":
        if "DS LAB" in upper:
            return "A-F3-05"
        if "JAVA LAB" in upper:
            return "A-F1-05"
    return None


def detect_conflicts(sessions: list[dict]) -> list[dict]:
    conflicts = []
    grouped: dict[tuple[str, str], list[tuple[int, dict]]] = {}
    for index, session in enumerate(sessions):
        grouped.setdefault((session["term_code"], session["day"]), []).append((index, session))
    seen = set()
    for (term_code, day), indexed in grouped.items():
        for i, first in indexed:
            for j, second in indexed:
                if j <= i:
                    continue
                overlap_start = max(first["start_period"], second["start_period"])
                overlap_end = min(first["end_period"], second["end_period"])
                if overlap_start > overlap_end:
                    continue
                ids = (i, j)
                for conflict_type in ("room", "faculty", "section"):
                    conflict = False
                    if conflict_type == "room":
                        conflict = (first["room_required"] and second["room_required"] and
                                    first["room_id"] is not None and first["room_id"] == second["room_id"])
                    elif conflict_type == "faculty":
                        conflict = bool(set(first["faculty_initials"]) & set(second["faculty_initials"]))
                    else:
                        conflict = first["section_code"] == second["section_code"]
                        batch_parallel = (first["batch"] in {"B1", "B2"} and second["batch"] in {"B1", "B2"}
                                          and first["batch"] != second["batch"]
                                          and first["block_id"] == second["block_id"]
                                          and first["room_id"] != second["room_id"])
                        conflict = conflict and not batch_parallel
                    key = (conflict_type, ids, overlap_start)
                    if conflict and key not in seen:
                        seen.add(key)
                        conflicts.append({"type": conflict_type, "term_code": term_code, "day": day,
                                          "period": overlap_start, "session_indices": [i, j]})
    return conflicts


def import_timetables(db: Session, path: Path = SPEC_PATH) -> str:
    parsed = parse_timetables(path)
    term_rows = {}
    for row in parsed.terms:
        term = db.scalar(select(AcademicTerm).where(AcademicTerm.code == row["code"]))
        if term is None:
            term = AcademicTerm(**row)
            db.add(term)
            db.flush()
        term_rows[row["code"]] = term
    imported_term_ids = [term.id for term in term_rows.values()]
    if imported_term_ids:
        session_ids = select(TimetableSession.id).where(
            TimetableSession.term_id.in_(imported_term_ids),
            TimetableSession.provenance.in_(("REAL_DSATM_PDF", "INFERRED")),
        )
        db.execute(delete(TimetableSessionFaculty).where(TimetableSessionFaculty.session_id.in_(session_ids)))
        db.execute(delete(TimetableSession).where(TimetableSession.id.in_(session_ids)))
    subject_rows, faculty_rows, section_rows = {}, {}, {}
    for row in parsed.subjects:
        key = (row["term_code"], row["code"])
        term_id = term_rows[row["term_code"]].id
        existing = db.scalar(select(TimetableSubject).where(TimetableSubject.term_id == term_id,
                                                            TimetableSubject.code == row["code"]))
        if existing is None:
            existing = TimetableSubject(term_id=term_id, code=row["code"], name=row["name"], provenance=row["provenance"])
            db.add(existing)
        else:
            existing.name, existing.provenance = row["name"], row["provenance"]
        subject_rows[key] = existing
    for row in parsed.faculty:
        key = (row["term_code"], row["initials"])
        term_id = term_rows[row["term_code"]].id
        existing = db.scalar(select(Faculty).where(Faculty.term_id == term_id,
                                                   Faculty.initials == row["initials"]))
        if existing is None:
            existing = Faculty(term_id=term_id, initials=row["initials"], full_name=row["full_name"], provenance=row["provenance"])
            db.add(existing)
        else:
            existing.full_name, existing.provenance = row["full_name"], row["provenance"]
        faculty_rows[key] = existing
    for row in parsed.sections:
        key = (row["term_code"], row["code"])
        term_id = term_rows[row["term_code"]].id
        room = db.scalar(select(Room).where(Room.number == row["home_room_id"])) if row["home_room_id"] else None
        existing = db.scalar(select(TimetableSection).where(TimetableSection.term_id == term_id,
                                                            TimetableSection.code == row["code"]))
        if existing is None:
            existing = TimetableSection(term_id=term_id, code=row["code"], name=row["name"],
                                        division_code=row["division_code"], home_room_id=room.id if room else None,
                                        provenance=row["provenance"])
            db.add(existing)
        else:
            existing.name, existing.division_code = row["name"], row["division_code"]
            existing.home_room_id = room.id if room else None
        section_rows[key] = existing
    db.flush()
    for row in parsed.sessions:
        term_id = term_rows[row["term_code"]].id
        section = section_rows[(row["term_code"], row["section_code"])]
        subject = subject_rows.get((row["term_code"], row["subject_code"])) if row["subject_code"] else None
        faculty_ids = [faculty_rows[(row["term_code"], initials)].id for initials in row["faculty_initials"]
                       if (row["term_code"], initials) in faculty_rows]
        room = db.scalar(select(Room).where(Room.number == row["room_id"])) if row["room_id"] else None
        session = TimetableSession(term_id=term_id, section_id=section.id, batch=row["batch"], day=row["day"],
                                   start_period=row["start_period"], end_period=row["end_period"],
                                   subject_id=subject.id if subject else None,
                                   faculty_id=faculty_ids[0] if faculty_ids else None,
                                   room_id=room.id if room else None, room_required=row["room_required"],
                                   room_inferred=row.get("room_inferred", False),
                                   raw_label=row["raw_label"], block_id=row["block_id"],
                                   provenance=row["provenance"], version=1)
        db.add(session)
        db.flush()
        for faculty_id in faculty_ids:
            db.add(TimetableSessionFaculty(session_id=session.id, faculty_id=faculty_id,
                                           provenance=row["provenance"]))
    db.commit()
    return _write_import_report(parsed)


def _write_import_report(parsed: ParsedTimetables) -> str:
    sessions_by_term = Counter(s["term_code"] for s in parsed.sessions)
    sessions_by_section = Counter(f"{s['term_code']} {s['section_code']}" for s in parsed.sessions)
    conflicts_by_type = Counter(c["type"] for c in parsed.conflicts)
    conflicts_by_term = Counter(f"{c['term_code']} {c['type']}" for c in parsed.conflicts)
    inferred_room_conflicts = sum(
        item["type"] == "room" and any(parsed.sessions[index].get("room_inferred", False)
                                        for index in item["session_indices"])
        for item in parsed.conflicts
    )
    roomless = sum(not s["room_required"] for s in parsed.sessions)
    inferred_room_assignments = sum(s.get("room_inferred", False) for s in parsed.sessions)
    report = [
        "## M2 Timetable Import Report",
        "",
        "Counts are parsed from the three timetable datasets; no clash was automatically corrected.",
        "- Sessions per term: " + (", ".join(f"{term}: {sessions_by_term[term]}" for term in sorted(sessions_by_term)) or "none"),
        "- Sessions per section: " + (", ".join(f"{section}: {sessions_by_section[section]}" for section in sorted(sessions_by_section)) or "none"),
        f"- Distinct rooms used by inferred room assignments: {len(parsed.inferred_rooms)}",
        f"- Sessions with an INFERRED room assignment: {inferred_room_assignments}",
        f"- Sessions with room_required=False: {roomless}",
        f"- Excluded B-Block lab entries: {parsed.excluded_b_block_labs}",
        "- Conflicts per type: " + (", ".join(f"{key}: {conflicts_by_type[key]}" for key in ("room", "faculty", "section")) or "room: 0, faculty: 0, section: 0"),
        "- Conflicts per term/type: " + (", ".join(f"{key}: {conflicts_by_term[key]}" for key in sorted(conflicts_by_term)) or "none"),
        f"- Room conflicts involving at least one inferred room assignment: {inferred_room_conflicts} (these are provisional pending room confirmation).",
        "",
        "### Detected source clashes",
    ]
    for item in parsed.conflicts:
        first, second = (parsed.sessions[index] for index in item["session_indices"])
        inferred_marker = " [inferred room assignment involved]" if item["type"] == "room" and any(
            parsed.sessions[index].get("room_inferred", False) for index in item["session_indices"]
        ) else ""
        report.append(
            f"- {item['term_code']} {item['type']} clash on {item['day']} P{item['period']}: "
            f"section {first['section_code']} `{first['raw_label']}` and "
            f"section {second['section_code']} `{second['raw_label']}`.{inferred_marker}"
        )
    if not parsed.conflicts:
        report.append("- None detected.")
    if parsed.parse_issues:
        report.extend(["", "### Parser notes", *[f"- {issue}" for issue in parsed.parse_issues]])
    report.append("")
    report_text = "\n".join(report)
    data_issues = SPEC_PATH.parent / "DATA_ISSUES.md"
    existing = data_issues.read_text(encoding="utf-8") if data_issues.exists() else "# Data Issues\n"
    existing = re.sub(r"\n## M2 Timetable Import Report\n[\s\S]*$", "", existing).rstrip()
    data_issues.write_text(existing + "\n\n" + report_text, encoding="utf-8")
    print(report_text)
    return report_text
