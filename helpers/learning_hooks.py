from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple, Optional

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


# --- New standardized strategy helpers (additive; backward compatible) ---
def get_strategy(
    logic_id: str, key: str, default: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    registry = load_strategy_registry(logic_id)
    # normalize storage to a dict of variants under `variants`
    variants: Dict[str, Any] = {}
    raw = registry.get("variants")
    if isinstance(raw, dict):
        variants = raw
    else:
        # migrate from list if needed (no rewrite; just wrap)
        variants = {}
    if key not in variants:
        variants[key] = default or {"weight": 1.0, "notes": []}
        registry["variants"] = variants
        save_strategy_registry(logic_id, registry)
    return variants[key]


def update_strategy_registry(
    logic_id: str, key: str, delta: Dict[str, Any]
) -> Dict[str, Any]:
    registry = load_strategy_registry(logic_id)
    variants: Dict[str, Any] = registry.get("variants") or {}
    cur = variants.get(key, {"weight": 1.0, "notes": []})
    cur.update({k: v for k, v in (delta or {}).items() if v is not None})
    variants[key] = cur
    registry["variants"] = variants
    save_strategy_registry(logic_id, registry)
    return cur


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


def score_confidence(*args, **kwargs) -> float:
    """
    Backward-compatible confidence scoring.
    - New signature: score_confidence(sample_size: int, anomalies: int, validations_failed: int)
    - Legacy signature: score_confidence(result: Dict, alerts: List[str], structural_keys=("result","provenance"))
    """
    # New-style kwargs path
    if {"sample_size", "anomalies", "validations_failed"} <= set(kwargs.keys()):
        try:
            sample_size = int(kwargs.get("sample_size", 1) or 1)
            anomalies = int(kwargs.get("anomalies", 0) or 0)
            validations_failed = int(kwargs.get("validations_failed", 0) or 0)
            base = min(1.0, 0.6 + min(sample_size, 100) / 400.0)
            penalty = 0.2 * min(1.0, anomalies / max(1.0, sample_size))
            penalty += 0.2 * min(1.0, validations_failed / max(1.0, sample_size))
            return max(0.0, min(1.0, base - penalty))
        except Exception:
            return 0.4

    # Legacy positional path
    result: Optional[Dict[str, Any]] = None
    alerts: Optional[List[str]] = None
    structural_keys: Tuple[str, ...] = ("result", "provenance")
    if len(args) >= 1:
        result = args[0]
    if len(args) >= 2:
        alerts = args[1]
    if len(args) >= 3 and isinstance(args[2], tuple):
        structural_keys = args[2]
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
            if isinstance(a, str) and (
                "error" in a.lower() or "unbalanced" in a.lower()
            ):
                base -= 0.1
        return max(0.1, min(0.95, base))
    except Exception:
        return 0.4
