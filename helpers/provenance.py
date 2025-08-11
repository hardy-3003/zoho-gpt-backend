from __future__ import annotations
from typing import Any, Dict


def make_provenance(**fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a normalized provenance map for key figures.
    { "field_name": {"source":"zoho", "endpoint":"<api>", "ids":[], "filters":{}} }
    """
    prov: Dict[str, Any] = {}
    for key, value in fields.items():
        v = value if isinstance(value, dict) else {"endpoint": str(value)}
        v.setdefault("source", "zoho")
        v.setdefault("ids", [])
        v.setdefault("filters", {})
        prov[key] = v
    return prov
