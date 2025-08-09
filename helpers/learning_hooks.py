from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

from .history_store import append_event


STRATEGY_DIR = os.path.join(os.getcwd(), "data", "strategies")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _strategy_path(logic_id: str) -> str:
    _ensure_dir(STRATEGY_DIR)
    safe_id = logic_id.replace("/", "_")
    return os.path.join(STRATEGY_DIR, f"{safe_id}.json")


def load_strategy_registry(logic_id: str) -> Dict[str, Any]:
    try:
        path = _strategy_path(logic_id)
        if not os.path.exists(path):
            return {"version": 1, "strategies": [], "notes": []}
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {"version": 1, "strategies": [], "notes": []}


def save_strategy_registry(logic_id: str, registry: Dict[str, Any]) -> None:
    try:
        path = _strategy_path(logic_id)
        with open(path, "w") as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)
    except Exception:
        # best-effort; do not throw inside logic
        pass


def record_feedback(logic_id: str, feedback: Dict[str, Any]) -> None:
    try:
        append_event(
            logic_id,
            {
                "type": "feedback",
                "payload": feedback,
                "signals": ["l4-v0-feedback"],
            },
        )
    except Exception:
        pass


def score_confidence(
    result: Dict[str, Any] | None = None,
    alerts: List[str] | None = None,
    structural_keys: Tuple[str, ...] = ("result", "provenance"),
) -> float:
    # Heuristic baseline: structure present + fewer alerts => higher confidence
    try:
        base = 0.6
        if not result:
            return 0.3
        missing = 0
        for k in structural_keys:
            if isinstance(result, dict) and k not in result:
                missing += 1
        base -= 0.1 * missing
        for a in alerts or []:
            if "error" in a.lower() or "unbalanced" in a.lower():
                base -= 0.1
        return max(0.1, min(0.95, base))
    except Exception:
        return 0.4
