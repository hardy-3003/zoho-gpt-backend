"""
Title: Api Based Third Party Integration Framework
ID: L-164
Tags: []
Required Inputs: schema://api_based_third_party_integration_framework.input.v1
Outputs: schema://api_based_third_party_integration_framework.output.v1
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
    "id": "L-164",
    "title": "3rd-Party Integration Framework",
    "tags": ["integrations", "api", "registry"],
}

_STATUS = {"healthy", "degraded", "down"}


def _validate_ifw(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        conns = result.get("connectors") or []
        healthy = 0
        down = 0
        for c in conns:
            if c.get("status") not in _STATUS:
                alerts.append("bad_status")
            if c.get("status") == "healthy":
                healthy += 1
            if c.get("status") == "down":
                down += 1
        totals = result.get("totals") or {}
        if totals.get("healthy") != healthy or totals.get("down") != down:
            alerts.append("totals_mismatch")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], _alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        signals.append(
            f"connectors_down:{int((result.get('totals') or {}).get('down', 0))}"
        )
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
                "summary": {"size": len(result.get("connectors") or [])},
            },
        )
    except Exception:
        pass
    return {"notes": signals[:3]}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    end_date: Optional[str] = payload.get("end_date")
    org_id: Optional[str] = payload.get("org_id")
    headers: Dict[str, str] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        conn_url = (
            f"{api_domain}/books/v3/integrations/connectors?organization_id={org_id}"
        )
        sources.append(conn_url)
        _ = get_json(conn_url, headers)

        connectors: List[Dict[str, Any]] = []
        result = {
            "as_of": end_date,
            "connectors": connectors,
            "totals": {"healthy": 0, "down": 0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_ifw(result)
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
