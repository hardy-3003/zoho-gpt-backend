from __future__ import annotations

from typing import Any, Dict

# Minimal per-logic schema registry; extend as needed
_INPUT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "L-001": {
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
}

_OUTPUT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "L-001": {
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
}


def get_input_schema(logic_id: str) -> Dict[str, Any]:
    return _INPUT_SCHEMAS.get(logic_id, {"type": "object"})


def get_output_schema(logic_id: str) -> Dict[str, Any]:
    return _OUTPUT_SCHEMAS.get(logic_id, {"type": "object"})
