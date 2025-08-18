"""
Stable JSON comparator with clear unified diff output.

- Sorts keys deterministically
- Pretty-prints with stable formatting
- Returns (equal: bool, diff_text: str)

Future: tolerances and ignore paths can be added as parameters.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Tuple
from difflib import unified_diff


def _stable_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, separators=(",", ": ")) + "\n"


def compare_json(expected: Dict[str, Any], actual: Dict[str, Any]) -> Tuple[bool, str]:
    exp_s = _stable_dumps(expected)
    act_s = _stable_dumps(actual)
    if exp_s == act_s:
        return True, ""
    diff_lines = list(
        unified_diff(
            exp_s.splitlines(keepends=True),
            act_s.splitlines(keepends=True),
            fromfile="expected.json",
            tofile="actual.json",
        )
    )
    return False, "".join(diff_lines)
