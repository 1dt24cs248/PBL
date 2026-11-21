import pytest

from app.dataset import parse_dataset
from app.room_resolver import resolve_room


@pytest.mark.parametrize("canonical,alias,_provenance", parse_dataset().aliases)
def test_every_seeded_alias_resolves(canonical, alias, _provenance):
    assert resolve_room(alias) == canonical


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("103 'A' BLOCK", "A-F1-03"),
        ("A 103", "A-F1-03"),
        ("103-A Block", "A-F1-03"),
        ("A Block 103", "A-F1-03"),
        ("@ A 305", "A-F3-05"),
        ("SH-2 'A' BLOCK", "A-G10"),
    ],
)
def test_common_source_label_forms_resolve(label, expected):
    assert resolve_room(label) == expected


def test_explicit_a_prefixed_aliases_remain_distinct_from_plain_numbers():
    assert resolve_room("A-108") == "A-F1-10"
    assert resolve_room("108") == "A-F1-08"
    assert resolve_room("A-409") == "A-F4-09"
    assert resolve_room("209") == "A-F2-12"
    assert resolve_room("211") == "A-F2-11"
    assert resolve_room("A-209") == "A-F2-12"
    assert resolve_room("A-211") == "A-F2-11"


def test_five_f_explicit_room_211_does_not_alias_to_f2_10():
    from app.timetable_import import parse_timetables

    parsed = parse_timetables()
    rows = [row for row in parsed.sessions if row["term_code"] == "2026-27-ODD"
            and row["section_code"] == "F" and "@ A 211" in row["raw_label"]]
    assert rows
    assert all(row["room_id"] == "A-F2-11" for row in rows)
    clashes = [row for row in parsed.conflicts if row["term_code"] == "2026-27-ODD"
               and row["type"] == "room" and row["day"] == "Thu" and row["period"] in (1, 2)
               and any(parsed.sessions[i]["section_code"] == "C" for i in row["session_indices"])
               and any(parsed.sessions[i]["section_code"] == "F" for i in row["session_indices"])]
    assert not clashes


def test_b_block_and_unknown_labels_are_not_resolved():
    assert resolve_room("B-101") is None
    assert resolve_room("unknown room") is None
