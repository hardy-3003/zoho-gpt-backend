"""
Structured JSON logger for observability baseline (P1.4.2).

Emits one JSON object per line with keys:
{ "ts": ISO8601, "level": "INFO|WARN|ERROR", "evt": "<name>",
  "trace_id": "<if available>", "evidence_id": "<if available>",
  "attrs": { ... } }

Tests can monkeypatch the sink via set_sink(callable) to capture logs.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

JsonDict = Dict[str, Any]


def _default_sink(payload: JsonDict) -> None:
    print(json.dumps(payload, separators=(",", ":")), file=sys.stdout, flush=True)


_SINK: Callable[[JsonDict], None] = _default_sink


def set_sink(sink: Callable[[JsonDict], None]) -> None:
    """Override the log sink (test-only hook)."""
    global _SINK
    _SINK = sink


def _iso_now() -> str:
    # ISO8601 with Z suffix; deterministic format (not value)
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def emit(
    evt: str,
    *,
    level: str = "INFO",
    attrs: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    evidence_id: Optional[str] = None,
) -> None:
    """Emit a structured JSON log line.

    Do not raise errors from logger; be best-effort.
    """
    try:
        payload: JsonDict = {
            "ts": _iso_now(),
            "level": level.upper(),
            "evt": evt,
        }
        if trace_id is not None:
            payload["trace_id"] = str(trace_id)
        if evidence_id is not None:
            payload["evidence_id"] = str(evidence_id)
        payload["attrs"] = attrs or {}
        _SINK(payload)
    except Exception:
        # Never let logging break business flow
        pass


def info(
    evt: str,
    *,
    attrs: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    evidence_id: Optional[str] = None,
) -> None:
    emit(evt, level="INFO", attrs=attrs, trace_id=trace_id, evidence_id=evidence_id)


def warn(
    evt: str,
    *,
    attrs: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    evidence_id: Optional[str] = None,
) -> None:
    emit(evt, level="WARN", attrs=attrs, trace_id=trace_id, evidence_id=evidence_id)


def error(
    evt: str,
    *,
    attrs: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    evidence_id: Optional[str] = None,
) -> None:
    emit(evt, level="ERROR", attrs=attrs, trace_id=trace_id, evidence_id=evidence_id)
