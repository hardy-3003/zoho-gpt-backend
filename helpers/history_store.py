from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict


# Resolve history directory relative to the repository root rather than the
# current working directory. Using ``os.getcwd()`` meant that importing this
# module from another location would write files outside the project tree.
# ``__file__`` always points to this module so we build paths from it.
BASE_DIR = Path(__file__).resolve().parent.parent / "data" / "history"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_event(stream: str, data: Dict[str, Any]) -> str:
    ts = int(time.time() * 1000)
    dir_path = BASE_DIR / stream
    _ensure_dir(dir_path)
    file_path = dir_path / f"{ts}.json"
    with open(file_path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(file_path)
