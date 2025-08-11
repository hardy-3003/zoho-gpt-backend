from __future__ import annotations
from typing import Any, Dict, List


REQUIRED_KEYS = ("source", "endpoint", "ids", "filters")


def _normalize_entry(v: Any) -> Dict[str, Any]:
    if not isinstance(v, dict):
        v = {"source": "zoho", "endpoint": str(v), "ids": [], "filters": {}}
    v.setdefault("source", "zoho")
    v.setdefault("endpoint", "")
    v.setdefault("ids", [])
    v.setdefault("filters", {})
    return v


def make_field_provenance(**fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Legacy field-based provenance map for backward compatibility:
    { "field_name": {"source":"zoho", "endpoint":"<api>", "ids":[], "filters":{}} }
    """
    prov: Dict[str, Any] = {}
    for key, value in fields.items():
        prov[key] = _normalize_entry(value)
    return prov


def make_provenance(**fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalized provenance map:
    { "sources": [{"source":"zoho", "endpoint":"<api>", "ids":[], "filters":{}}] }
    """
    sources: List[Dict[str, Any]] = []
    for key, value in fields.items():
        normalized = _normalize_entry(value)
        sources.append(normalized)

    # If no fields provided, return default structure
    if not sources:
        sources = [
            {"source": "zoho", "endpoint": "reports/auto", "ids": [], "filters": {}}
        ]

    return {"sources": sources}


def validate_provenance(prov: Dict[str, Any]) -> None:
    if not isinstance(prov, dict):
        raise TypeError("provenance must be a dict")
    # Support composite provenance with 'figures' and 'sources'
    entries = prov.get("figures") if isinstance(prov.get("figures"), dict) else prov
    for field, entry in entries.items():
        # Skip audit_trail entries which have a different structure
        if field == "audit_trail":
            continue
        # ignore non-dict top-level keys like 'sources'
        if field == "sources":
            continue
        if not isinstance(entry, dict):
            raise TypeError(f"provenance[{field}] must be a dict")
        for rk in REQUIRED_KEYS:
            if rk not in entry:
                raise ValueError(f"provenance[{field}] missing `{rk}`")
        if not isinstance(entry["endpoint"], str):
            raise TypeError(f"provenance[{field}].endpoint must be str")
        if not isinstance(entry["ids"], list):
            raise TypeError(f"provenance[{field}].ids must be list")
        if not isinstance(entry["filters"], dict):
            raise TypeError(f"provenance[{field}].filters must be dict")
