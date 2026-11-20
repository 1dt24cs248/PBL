"""Regenerate the committed, fully synthetic A-Block floorplan artifact."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.floorplan_generator import generate_floorplan  # noqa: E402

OUTPUT = BACKEND_DIR / "data" / "synthetic" / "floorplan.json"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(generate_floorplan(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote synthetic floorplan to {OUTPUT}")


if __name__ == "__main__":
    main()
