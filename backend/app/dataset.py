"""Parser for the checked-in, authoritative Markdown dataset specification."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


SPEC_PATH = Path(__file__).resolve().parents[2] / "docs" / "dataset_spec.md"


@dataclass
class Dataset:
    rooms: list[dict]
    aliases: list[tuple[str, str, str]]
    equipment: list[dict]
    students: list[dict]
    sections: list[dict]
    holidays: list[dict]
    inferred: list[str]


def parse_dataset(path: Path = SPEC_PATH) -> Dataset:
    text = path.read_text(encoding="utf-8")
    rooms = _parse_rooms(text)
    inferred = []
    # These two additional room identifiers are expressly requested by M1 but
    # absent from the source CSV; floor is inferred from their identifier.
    for room_id in ("A-F2-11", "A-F2-12"):
        rooms.append({
            "room_id": room_id, "building_id": "A", "building_name": "A Block",
            "floor_number": 2, "floor_name": "Second Floor", "room_name": "Unspecified room",
            "facility_type": "Unspecified", "department": "Shared", "capacity_students": 0,
            "estimated_connected_load_kw": 0.0, "timetable_eligible": False,
            "data_status": "INFERRED", "provenance": "INFERRED",
            "notes": "Added per M1; no source specifications were supplied.",
        })
        inferred.append(f"{room_id}: added per M1; floor 2 inferred from ID; name, type, capacity, load, and eligibility remain unspecified (zero/false placeholders).")
    aliases = _parse_aliases(text)
    if any(provenance == "INFERRED" for _, _, provenance in aliases):
        inferred.append("A-409: alias is documented against the A-F4-06–10 range; resolved to A-F4-09 from its room number and the floor/room numbering rule.")
    students, sections, roster_issues = _parse_students(text)
    inferred.extend(roster_issues)
    inferred.append("CSE division to 5th-semester section mapping is the requested inferred admin-editable mapping: " + ", ".join(f"CSE-{n}->{chr(64+n)}" for n in range(1, 7)) + ".")
    division_totals = {section["code"]: sum(s["section_code"] == section["code"] for s in students)
                       for section in sections}
    for section in sections:
        actual = division_totals[section["code"]]
        declared = section["declared_student_count"]
        if actual != declared:
            inferred.append(f"{section['code']}: roster parser finds {actual} assigned student rows but heading declares {declared}; source memberships preserved without reallocation.")
    equipment = []
    energy_kw = {}
    for room in rooms:
        items = _equipment_for(room["room_id"])
        for item in items:
            equipment.append({"room_id": room["room_id"], **item})
        energy_kw[room["room_id"]] = sum(i["quantity"] * i["watts_each"] for i in items) / 1000
    for i, room in enumerate(rooms, 1):
        room["energy_baseline_code"] = f"EN{i:04d}"
        room["energy_connected_load_kw"] = energy_kw[room["room_id"]]
    inferred.append("Energy baseline connected loads are calculated from the synthetic equipment wattage rules (not copied from room CSV estimates); for example A-G04 is 0.71 kW in the baseline and 2.5 kW in the room estimate, retained separately.")
    if len(equipment) != 129:
        raise ValueError(f"Expected 129 equipment rows from rules, parsed {len(equipment)}")
    # Only this confirmed holiday is in scope; the date is provided by M1.
    holidays = [{"holiday_date": "2026-11-10", "name": "Deepavali 2026", "provenance": "INFERRED"}]
    inferred.append("Deepavali 2026-11-10: date/name supplied by M1; holiday status is not evidenced in the dataset spec, so tagged INFERRED.")
    return Dataset(rooms, aliases, equipment, students, sections, holidays, inferred)


def _parse_rooms(text: str) -> list[dict]:
    start = re.search(r"#### A\. Rooms CSV \(64 rows\)\s*```csv\s*", text)
    end = re.search(r"\nB\. Equipment & Energy Baseline Rules", text[start.end():]) if start else None
    if not start or not end:
        raise ValueError("Could not find the Rooms CSV block")
    rows = list(csv.DictReader(text[start.end():start.end() + end.start()].splitlines()))
    if len(rows) != 64:
        raise ValueError(f"Expected 64 room rows, found {len(rows)}")
    parsed = []
    for row in rows:
        if row["building_id"] != "A" or row["room_id"].startswith("B-"):
            continue
        parsed.append({
            **row, "floor_number": int(row["floor_number"]),
            "capacity_students": int(row["capacity_students"]),
            "estimated_connected_load_kw": float(row["estimated_connected_load_kw"]),
            "timetable_eligible": row["timetable_eligible"].lower() == "true",
            "provenance": "SYNTHETIC",
        })
    return parsed


def _parse_students(text: str) -> tuple[list[dict], list[dict], list[str]]:
    roster_start = text.index("Complete Official DSATM CSE Student Roster")
    roster_text = text[roster_start:]
    division_matches = list(re.finditer(
        r"Division (CSE-[1-6]) \| Room: (.*?) \| (\d+) Students\s*\n(.*?)(?=\nDivision CSE-|\n\(Also include|\Z)",
        roster_text, re.S,
    ))
    if len(division_matches) != 6:
        raise ValueError(f"Expected six division roster sections, found {len(division_matches)}")
    students: list[dict] = []
    sections: list[dict] = []
    issues: list[str] = []
    seen_usns = set()
    admission_rows = 0
    addendum_rows = 0
    for match in division_matches:
        division, header, declared, body = match.groups()
        room_match = re.search(r"\((A-[A-Z0-9-]+)", header)
        if not room_match:
            raise ValueError(f"No canonical A-Block home room found in {division} heading")
        section = {"code": division, "name": division, "home_room_id": room_match.group(1),
                   "declared_student_count": int(declared), "provenance": "REAL_DSATM_PDF"}
        sections.append(section)
        for entry in re.split(r"\s*\|\s*", body.strip()):
            entry = entry.strip().rstrip(".")
            parsed = re.match(r"(?P<identifier>(?:1DT24CS\d{3}|24UGDT[\w-]+))\s+(?P<rest>.+?)\s+\((?P<gender>[MF]),\s*(?P<batch>A[12])\)$", entry)
            if not parsed:
                continue
            identifier, rest, gender, batch = parsed.groups()
            usn = identifier if re.fullmatch(r"1DT24CS\d{3}", identifier) else None
            # A slash is a documented source ambiguity: retain the exact name string.
            full_name = rest.strip()
            if usn and usn in seen_usns:
                raise ValueError(f"Duplicate USN {usn}")
            if usn:
                seen_usns.add(usn)
            else:
                admission_rows += 1
            students.append({"usn": usn, "source_identifier": None if usn else identifier,
                             "full_name": full_name, "gender": gender, "lab_batch": batch,
                             "section_code": division, "provenance": "REAL_DSATM_PDF"})
    if admission_rows:
        issues.append(f"{admission_rows} admission-number roster entries are not official USNs; NULL USN stored and source identifiers retained in the database.")
    # Parse the explicitly named roster addendum without hand-entering student rows.
    addendum = re.search(r"\(Also include (.*?) from the master", roster_text, re.S)
    if addendum:
        for usn, name in re.findall(r"(1DT24CS\d{3})\s+([^,]+?)(?=,\s*1DT24CS|\s+from the master)", addendum.group(1) + " from the master"):
            if usn in seen_usns:
                continue
            number = int(usn[-3:])
            section_code = f"CSE-{min((number - 1) // 58 + 1, 6)}"
            students.append({"usn": usn, "source_identifier": None, "full_name": name.strip(),
                             "gender": None, "lab_batch": None, "section_code": section_code,
                             "provenance": "REAL_DSATM_PDF"})
            seen_usns.add(usn)
            addendum_rows += 1
    if addendum_rows:
        issues.append(f"{addendum_rows} explicit master-list addendum records have no gender/batch; those fields remain NULL; divisions are derived from USN sequence.")
    return students, sections, issues


def _parse_aliases(text: str) -> list[tuple[str, str, str]]:
    aliases = []
    # Only the dedicated room directory is authoritative for aliases. In
    # particular, the Rooms CSV's notes column can mention nearby room labels
    # and must never create resolver mappings.
    directory = text.split("#### A. Rooms CSV", 1)[0]
    for line in directory.splitlines():
        if "(alias " not in line:
            continue
        cells = line.split("|")
        if len(cells) < 4:
            continue
        canonical_text = re.sub(r"[*]", "", cells[2]).strip()
        canonical = re.search(r"(A-[A-Z0-9-]+)", canonical_text)
        names = re.search(r"\(alias ([^)]+)\)", canonical_text)
        if not canonical or not names:
            continue
        base_label = canonical_text.split("(alias")[0].strip()
        room_range = re.search(r"A-F(\d)-(\d+)[–-](\d+)", base_label)
        provenance = "INFERRED" if room_range else "REAL_DSATM_PDF"
        for alias in names.group(1).split("/"):
            alias = alias.strip()
            room_id = canonical.group(1)
            if room_range:
                digits = re.search(r"(\d{3})$", alias)
                floor, first, last = map(int, room_range.groups())
                if digits:
                    alias_floor, room_number = divmod(int(digits.group(1)), 100)
                    if alias_floor == floor and first <= room_number <= last:
                        room_id = f"A-F{floor}-{room_number:02d}"
            aliases.append((room_id, alias, provenance))
    # Plain three-digit classroom labels: floor hundreds + room suffix.
    for floor in range(1, 6):
        max_number = 10 if floor < 5 else 4
        for room_number in range(1, max_number + 1):
            token = str(floor * 100 + room_number)
            aliases.append((f"A-F{floor}-{room_number:02d}", token, "REAL_DSATM_PDF"))
    # Explicit aliases override numeric floor/room inference. 209 and 211 are
    # separate physical rooms; notes on the F2-10 CSV row are not aliases.
    aliases.extend([
        ("A-G03", "SH1", "REAL_DSATM_PDF"), ("A-G10", "SH-2", "REAL_DSATM_PDF"),
        ("A-F2-06", "206", "REAL_DSATM_PDF"), ("A-F2-10", "210", "REAL_DSATM_PDF"),
        ("A-F3-05", "305", "REAL_DSATM_PDF"), ("A-F5-06", "506", "REAL_DSATM_PDF"),
        ("A-F5-02", "502", "REAL_DSATM_PDF"), ("A-F5-05", "505", "REAL_DSATM_PDF"),
        ("A-F4-09", "409", "INFERRED"), ("A-F2-05", "205", "REAL_DSATM_PDF"),
        ("A-F2-12", "209", "REAL_DSATM_PDF"), ("A-F2-12", "A-209", "REAL_DSATM_PDF"),
        ("A-F2-11", "211", "REAL_DSATM_PDF"), ("A-F2-11", "A-211", "REAL_DSATM_PDF"),
    ])
    by_alias = {}
    for room_id, alias, provenance in aliases:
        by_alias[alias] = (room_id, alias, provenance)
    return list(by_alias.values())


def _equipment_for(room_id: str) -> list[dict]:
    def items(*pairs):
        return [{"name": name, "quantity": count, "watts_each": watts, "provenance": "SYNTHETIC"}
                for name, count, watts in pairs]
    if room_id in {"A-F2-11", "A-F2-12"}:
        return []
    if room_id in {"A-G04", "A-G05", *(f"A-F{floor}-{n:02d}" for floor in range(1, 6) for n in range(1, 5))}:
        return items(("LED", 8, 20), ("Fan", 4, 75), ("Projector", 1, 250))
    if room_id in {"A-G07", *(f"A-F{floor}-05" for floor in range(1, 6))}:
        return items(("LED", 10, 20), ("Fan", 4, 75), ("Desktop", 30, 150), ("Network switch", 2, 40))
    if room_id == "A-G03":
        return items(("LED", 12, 20), ("Fan", 6, 75), ("Projector", 2, 250))
    if room_id == "A-B03":
        return items(("LED", 8, 20), ("Workshop equipment", 4, 500))
    return items(("LED", 2, 20))
