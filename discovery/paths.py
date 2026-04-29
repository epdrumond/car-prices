import json
from pathlib import Path
from typing import Any

DISCOVERY_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = DISCOVERY_DIR / "output"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
