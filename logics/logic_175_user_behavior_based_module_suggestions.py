"""
Title: User Behavior Based Module Suggestions
ID: L-175
Tags: []
Required Inputs: schema://user_behavior_based_module_suggestions.input.v1
Outputs: schema://user_behavior_based_module_suggestions.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only.
"""
from typing import Dict, Any, List, Optional

try:
    from helpers.zoho_client import get_json
except Exception:

    def get_json(url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        return {}


try:
    from helpers.history_store import append_event
except Exception:

    def append_event(*args, **kwargs) -> None:
        return None


LOGIC_META = {
    "id": "L-175",
    "title": "User Behavior Based Module Suggestions",
    "tags": ["usage", "suggestions", "ux"],
}


def _validate_ubms(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    valid = {"low", "med", "high"}
    suggestions = result.get("suggestions") or []
    high = 0
    for s in suggestions:
        pr = s.get("priority")
        if pr not in valid:
            alerts.append("invalid_priority")
        if not (s.get("reason") or "").strip():
            alerts.append("empty_reason")
        if pr == "high":
            high += 1
    totals = result.get("totals") or {}
    if int(totals.get("high", 0)) != int(high):
        alerts.append("totals_mismatch")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        high = int((result.get("totals") or {}).get("high", 0))
        signals.append(f"high_suggestions:{high}")
        if alerts:
            signals.append("alert:present")
    except Exception:
        pass
    try:
        append_event(
            LOGIC_META["id"],
            {
                "org_id": payload.get("org_id"),
                "period": {
                    "start": payload.get("start_date"),
                    "end": payload.get("end_date"),
                },
                "signals": signals,
            },
        )
    except Exception:
        pass
    return {"notes": signals[:3]}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    org_id: Optional[str] = payload.get("org_id")
    start_date: Optional[str] = payload.get("start_date")
    end_date: Optional[str] = payload.get("end_date")
    headers: Dict[str, str] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        suggestions: List[Dict[str, Any]] = []
        result = {
            "as_of": end_date,
            "suggestions": suggestions,
            "totals": {
                "high": sum(1 for s in suggestions if s.get("priority") == "high")
            },
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_ubms(result)
    learn = _learn_from_history(payload, result, alerts)
    conf = 0.6 - (0.15 if alerts else 0.0) - (0.1 if not result else 0.0)
    conf = max(0.1, min(0.95, conf))
    return {
        "result": result,
        "provenance": {"sources": sources},
        "confidence": conf,
        "alerts": alerts,
        "meta": {
            "strategy": "l4-v0",
            "org_id": org_id,
            "query": query,
            "notes": learn.get("notes", []),
        },
    }
