from collections import Counter

from app.timetable_import import detect_conflicts, parse_timetables


def test_all_timetable_terms_parse_and_stay_a_block_only():
    parsed = parse_timetables()
    assert {term["code"] for term in parsed.terms} == {
        "2026-27-ODD", "2025-26-ODD", "2024-25-EVEN"
    }
    assert Counter(session["term_code"] for session in parsed.sessions) == {
        "2026-27-ODD": 171, "2025-26-ODD": 177, "2024-25-EVEN": 115
    }
    assert all(not (session["room_id"] or "").startswith("B-") for session in parsed.sessions)
    assert parsed.excluded_b_block_labs == 10
    assert all(session["room_required"] or session["room_id"] is None for session in parsed.sessions)
    assert {faculty["initials"] for faculty in parsed.faculty if faculty["term_code"] == "2026-27-ODD"}
    assert any(subject["code"] == "B**K509" for subject in parsed.subjects)
    assert any(subject["code"] == "BCSK308" for subject in parsed.subjects)


def test_fifth_semester_regressions_and_batches():
    parsed = parse_timetables()
    sessions = parsed.sessions
    e_wed = [row for row in sessions if row["term_code"] == "2026-27-ODD"
             and row["section_code"] == "E" and row["day"] == "Wed"]
    selected = {(row["start_period"], row["subject_code"]): row for row in e_wed}
    assert selected[(1, "BCS502")]["room_id"] == "A-F1-01"
    assert selected[(1, "BCS502")]["faculty_initials"] == ["PP"]
    assert selected[(5, "BCS515B")]["faculty_initials"] == ["UCR"]
    assert selected[(6, "BCS501")]["faculty_initials"] == ["MS"]

    a_monday = [row for row in sessions if row["term_code"] == "2026-27-ODD"
                and row["section_code"] == "A" and row["day"] == "Mon"]
    # The room is attached to the 5A timetable section, not inferred from a student roster row.
    assert next(section for section in parsed.sections
                if section["term_code"] == "2026-27-ODD" and section["code"] == "A")["home_room_id"] == "A-F2-02"

    d_thu = next(row for row in sessions if row["term_code"] == "2026-27-ODD"
                 and row["section_code"] == "D" and row["day"] == "Thu" and row["start_period"] == 1)
    assert (d_thu["end_period"], d_thu["subject_code"], d_thu["room_id"]) == (2, "BCS502", "A-F3-05")
    parallel = [row for row in a_monday if row["batch"] in {"B1", "B2"}]
    parallel = [row for row in sessions if row["term_code"] == "2026-27-ODD"
                and row["section_code"] == "A" and row["day"] == "Wed" and row["batch"] in {"B1", "B2"}]
    assert {row["room_id"] for row in parallel} == {"A-F2-10", "A-F2-06"}
    assert len({row["block_id"] for row in parallel}) == 1


def test_batch_parallelism_allowed_and_real_conflicts_remain_reportable():
    parsed = parse_timetables()
    parallel = [row for row in parsed.sessions if row["term_code"] == "2026-27-ODD"
                and row["section_code"] == "A" and row["day"] == "Wed"
                and row["batch"] in {"B1", "B2"}]
    conflicts = detect_conflicts(parallel)
    assert not [item for item in conflicts if item["type"] == "section"]
    assert parsed.conflicts
    assert {item["type"] for item in parsed.conflicts} == {"room", "faculty"}
    assert all(item["type"] in {"room", "faculty", "section"} for item in parsed.conflicts)
