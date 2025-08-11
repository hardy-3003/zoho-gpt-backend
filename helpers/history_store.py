from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional


_ROOT = os.environ.get("DATA_DIR") or os.path.join(os.getcwd(), "data")
BASE_DIR = os.path.join(_ROOT, "history")

# Optional analyzers (best-effort)
try:
    from analyzers.delta_compare import period_delta  # type: ignore
except Exception:  # pragma: no cover

    def period_delta(current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore
        return {}


try:
    from analyzers.anomaly_engine import find_simple_anomalies  # type: ignore
except Exception:  # pragma: no cover

    def find_simple_anomalies(current: Dict[str, Any]) -> List[str]:  # type: ignore
        return []


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


def append_event(logic_id: str, data: Dict[str, Any]) -> str:
    """Compat helper expected by some logics.

    Stores under data/history/logic_{logic_id}/<ts>.json
    """
    stream = f"logic_{logic_id}"
    return write_event(stream, data)


def _events_dir_for(logic_id: str) -> str:
    return os.path.join(BASE_DIR, f"logic_{logic_id}")


def _read_latest_output_payload(logic_id: str) -> Optional[Dict[str, Any]]:
    dir_path = _events_dir_for(logic_id)
    if not os.path.isdir(dir_path):
        return None
    try:
        files = sorted(os.listdir(dir_path), reverse=True)
        for name in files:
            if not name.endswith(".json"):
                continue
            file_path = os.path.join(dir_path, name)
            with open(file_path, "r") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("type") == "outputs":
                payload = data.get("payload")
                if isinstance(payload, dict):
                    return payload
    except Exception:
        return None
    return None


def log_with_deltas_and_anomalies(
    logic_id: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    provenance: Dict[str, Any],
    period_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Single-call integration: history write + delta comparison + anomaly detection.
    Returns {alerts: [...], deltas: [...], anomalies: [...]} using simple analyzers.
    """
    try:
        append_event(
            logic_id, {"type": "inputs", "payload": inputs, "provenance": provenance}
        )
        append_event(
            logic_id, {"type": "outputs", "payload": outputs, "provenance": provenance}
        )
    except Exception:
        pass

    deltas: List[str] = []
    try:
        prev = _read_latest_output_payload(logic_id)
        if prev:
            delta_map = period_delta(outputs or {}, prev or {})
            if delta_map:
                deltas.append("delta: computed period difference")
    except Exception:
        # non-fatal
        pass

    anomalies: List[str] = []
    try:
        anomalies = find_simple_anomalies(outputs or {}) or []
    except Exception:
        pass

    alerts: List[str] = []
    alerts.extend(deltas)
    alerts.extend(anomalies)
    try:
        append_event(logic_id, {"type": "alerts", "payload": alerts})
    except Exception:
        pass
    return {"alerts": alerts, "deltas": deltas, "anomalies": anomalies}
