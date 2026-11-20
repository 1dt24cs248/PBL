"""Resolve timetable room labels to canonical A-Block room identifiers."""
from __future__ import annotations

import re

from .dataset import parse_dataset


def _compact(token: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", token.upper())


def _build_lookup() -> dict[str, str]:
    dataset = parse_dataset()
    lookup = {_compact(room["room_id"]): room["room_id"] for room in dataset.rooms}
    for room_id, alias, _ in dataset.aliases:
        lookup[_compact(alias)] = room_id
    return lookup


_ROOM_LOOKUP = _build_lookup()


def resolve_room(token: str | None) -> str | None:
    """Return a canonical A-Block room ID, or None when the label is unknown.

    The resolver accepts the source aliases and common timetable spellings,
    including labels where ``A`` or ``A Block`` appears before or after the
    numeric room label. It intentionally does not guess B-Block rooms.
    """
    if not token or not token.strip():
        return None
    compact = _compact(token)
    if compact.startswith("B"):
        return None
    if compact in _ROOM_LOOKUP:
        return _ROOM_LOOKUP[compact]
    # Common labels such as "SH-2 'A' BLOCK" and "Seminar Hall 1 - A block".
    if "SH2" in compact:
        return _ROOM_LOOKUP.get("SH2")
    if "SH1" in compact or "SEMINARHALL1" in compact:
        return _ROOM_LOOKUP.get("SH1")
    # Canonical IDs with arbitrary whitespace/punctuation.
    canonical = re.search(r"AF([1-5])(\d{2})", compact)
    if canonical:
        return _ROOM_LOOKUP.get(f"AF{canonical.group(1)}{canonical.group(2)}")
    # A-prefixed legacy numbers (A-108, A-209...) are distinct from plain
    # numeric floor/room labels, so try their full alias before stripping A.
    a_prefixed = re.fullmatch(r"A(\d{3})", compact)
    if a_prefixed and compact in _ROOM_LOOKUP:
        return _ROOM_LOOKUP[compact]
    # Match a plain 3-digit floor/room label embedded in arbitrary text.
    number = re.search(r"(?<!\d)([1-5]\d{2})(?!\d)", token)
    if number:
        return _ROOM_LOOKUP.get(number.group(1))
    return None
