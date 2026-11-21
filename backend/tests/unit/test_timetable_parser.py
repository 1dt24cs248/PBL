from collections import Counter

from app.timetable_import import detect_conflicts, parse_timetables


def test_all_timetable_terms_parse_and_stay_a_block_only():
    parsed = parse_timetables()
    assert {term["code"] for term in parsed.terms} == {
        "2026-27-ODD", "2025-26-ODD", "2024-25-EVEN"
    }
    assert Counter(session["term_code"] for session in parsed.sessions) == {
        "2026-27-ODD": 177, "2025-26-ODD": 183, "2024-25-EVEN": 115
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


def test_5c_thursday_reverse_batch_order_preserves_both_explicit_rooms():
    parsed = parse_timetables()
    c_thursday = [row for row in parsed.sessions if row["term_code"] == "2026-27-ODD"
                  and row["section_code"] == "C" and row["day"] == "Thu"
                  and row["start_period"] == 1]
    by_batch = {row["batch"]: row for row in c_thursday}
    assert set(by_batch) == {"B1", "B2"}
    assert by_batch["B1"]["room_id"] == "A-F2-06"  # explicit 206
    assert by_batch["B2"]["room_id"] == "A-F2-10"  # explicit 210
    assert by_batch["B1"]["block_id"] == by_batch["B2"]["block_id"]
    assert all(not row["room_inferred"] for row in by_batch.values())

    # 5F explicitly labels the same canonical room as 211; 211 aliases 210.
    # Only the B2 branch (210/A-F2-10) clashes, never B1 (206/A-F2-06).
    conflicts = [item for item in parsed.conflicts if item["term_code"] == "2026-27-ODD"
                 and item["day"] == "Thu" and item["period"] in (1, 2)
                 and item["type"] == "room"]
    assert len(conflicts) == 2
    for conflict in conflicts:
        first, second = (parsed.sessions[index] for index in conflict["session_indices"])
        assert {first["section_code"], second["section_code"]} == {"C", "F"}
        assert "B2:" in next(row for row in (first, second) if row["section_code"] == "C")["raw_label"]
