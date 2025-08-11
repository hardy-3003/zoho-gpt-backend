"""
Title: Free Resource Usage Estimator Power Tools Etc
ID: L-198
Tags: []
Required Inputs: schema://free_resource_usage_estimator_power_tools_etc.input.v1
Outputs: schema://free_resource_usage_estimator_power_tools_etc.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only.
"""
from typing import Dict, Any, List

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
    "id": "L-198",
    "title": "Free Resource Usage Estimator (Power, Tools, etc.)",
    "tags": ["usage", "leakage", "estimate"],
}


def _validate_usage(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    for r in result.get("estimates", []) or []:
        try:
            pct = float(r.get("usage_est_pct", 0.0))
            if pct < 0 or pct > 100:
                alerts.append("pct_out_of_bounds")
            basis = float(r.get("basis_value", 0.0))
            leak = float(r.get("value_leak", 0.0))
            if abs(leak - basis * pct / 100.0) > 0.0001:
                alerts.append("leak_mismatch")
        except Exception:
            alerts.append("invalid_estimate")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        append_event(
            LOGIC_META["id"],
            {
                "org_id": payload.get("org_id"),
                "period": {
                    "start": payload.get("start_date"),
                    "end": payload.get("end_date"),
                },
                "signals": ["l4-v0-run", "schema:stable"],
            },
        )
    except Exception:
        pass
    return {"notes": []}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    org_id = payload.get("org_id")
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    headers = payload.get("headers", {})
    api_domain = payload.get("api_domain", "")
    query = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        result = {
            "period": {"start": start_date, "end": end_date},
            "estimates": [],
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_usage(result)
    learn = _learn_from_history(payload, result)
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
