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


def test_b_block_and_unknown_labels_are_not_resolved():
    assert resolve_room("B-101") is None
    assert resolve_room("unknown room") is None
