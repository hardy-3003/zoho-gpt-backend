from __future__ import annotations

import os
from typing import Any, Dict

# Minimal per-logic schema registry with sensible defaults
_BASE_INPUT: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "org_id": {"type": "string"},
        "start_date": {"type": "string", "format": "date"},
        "end_date": {"type": "string", "format": "date"},
        "headers": {"type": "object"},
        "api_domain": {"type": "string"},
        "query": {"type": "string"},
    },
    "required": ["org_id", "start_date", "end_date"],
    "additionalProperties": True,
}

_BASE_OUTPUT: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "result": {"type": "object"},
        "provenance": {"type": "object"},
        "confidence": {"type": "number"},
        "alerts": {"type": "array", "items": {"type": "string"}},
        "meta": {"type": "object"},
    },
    "required": ["result", "provenance", "confidence", "alerts", "meta"],
}

_INPUT_SCHEMAS: Dict[str, Dict[str, Any]] = {"L-001": _BASE_INPUT}
_OUTPUT_SCHEMAS: Dict[str, Dict[str, Any]] = {"L-001": _BASE_OUTPUT}


def register_logic_schema(
    logic_id: str,
    input_schema: Dict[str, Any] | None = None,
    output_schema: Dict[str, Any] | None = None,
) -> None:
    if not logic_id:
        return
    _INPUT_SCHEMAS[logic_id] = input_schema or _BASE_INPUT
    _OUTPUT_SCHEMAS[logic_id] = output_schema or _BASE_OUTPUT


def get_input_schema(logic_id: str) -> Dict[str, Any]:
    return _INPUT_SCHEMAS.get(logic_id, _BASE_INPUT)


def get_output_schema(logic_id: str) -> Dict[str, Any]:
    return _OUTPUT_SCHEMAS.get(logic_id, _BASE_OUTPUT)


def ensure_all_logic_defaults(ids: list[str]) -> None:
    for lid in ids:
        _INPUT_SCHEMAS.setdefault(lid, _BASE_INPUT)
        _OUTPUT_SCHEMAS.setdefault(lid, _BASE_OUTPUT)


# --- Additive contract validation helpers ---
_OUTPUT_REQUIREMENTS = {
    "provenance": dict,
    "confidence": (int, float),
    "result": dict,
    "alerts": list,
}


def validate_output_contract(payload: Dict[str, Any]) -> None:
    for field, typ in _OUTPUT_REQUIREMENTS.items():
        if field not in payload:
            raise ValueError(f"Missing required output field: {field}")
        if not isinstance(payload[field], typ):
            raise TypeError(
                f"Field `{field}` must be {typ}, got {type(payload[field])}"
            )


def register_schema(
    logic_id: str, input_schema_ref: str, output_schema_ref: str
) -> None:
    # Placeholder for future external registry integration
    if not logic_id:
        return
