from __future__ import annotations

from typing import Any, Dict


def period_delta(current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k in set(current.keys()) | set(previous.keys()):
        try:
            out[k] = float(current.get(k, 0) or 0) - float(previous.get(k, 0) or 0)
        except Exception:
            # non-numeric fields ignored
            continue
    return out
