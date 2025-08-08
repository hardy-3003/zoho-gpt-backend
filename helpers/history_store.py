from __future__ import annotations

import json
import os
import time
from typing import Any, Dict


BASE_DIR = os.path.join(os.getcwd(), "data", "history")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_event(stream: str, data: Dict[str, Any]) -> str:
    ts = int(time.time() * 1000)
    dir_path = os.path.join(BASE_DIR, stream)
    _ensure_dir(dir_path)
    file_path = os.path.join(dir_path, f"{ts}.json")
    with open(file_path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return file_path
