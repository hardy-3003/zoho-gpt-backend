"""
Title: Data Redundancy Detector
ID: L-148
Tags: []
Required Inputs: schema://data_redundancy_detector.input.v1
Outputs: schema://data_redundancy_detector.output.v1
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
    "id": "L-148",
    "title": "Data Redundancy Detector",
    "tags": ["master", "duplicate", "data-quality"],
}

_REASONS = {"name-sim", "email", "gstin", "sku"}


def _validate_drd(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    suspects = result.get("suspects") or []
    try:
        for s in suspects:
            if s.get("a") == s.get("b"):
                alerts.append("self_pair")
            if s.get("reason") not in _REASONS:
                alerts.append("bad_reason")
        if (result.get("totals") or {}).get("count", 0) != len(suspects):
            alerts.append("count_mismatch")
        if suspects:
            alerts.append("dup_present")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        signals.append("dup:present" if result.get("suspects") else "dup:none")
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
                "summary": {"size": len(result.get("suspects") or [])},
            },
        )
    except Exception:
        pass
    return {"notes": signals[:3]}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    org_id: Optional[str] = payload.get("org_id")
    end_date: Optional[str] = payload.get("end_date")
    headers: Dict[str, str] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        cust_url = f"{api_domain}/books/v3/customers?organization_id={org_id}"
        vend_url = f"{api_domain}/books/v3/vendors?organization_id={org_id}"
        item_url = f"{api_domain}/books/v3/items?organization_id={org_id}"
        sources.extend([cust_url, vend_url, item_url])
        _ = get_json(cust_url, headers)
        _ = get_json(vend_url, headers)
        _ = get_json(item_url, headers)

        suspects: List[Dict[str, Any]] = []
        result = {
            "as_of": end_date,
            "suspects": suspects,
            "totals": {"count": len(suspects)},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_drd(result)
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
