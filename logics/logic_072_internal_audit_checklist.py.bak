"""
Title: Internal Audit Checklist
ID: L-072
Tags: []
Required Inputs: schema://internal_audit_checklist.input.v1
Outputs: schema://internal_audit_checklist.output.v1
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
    "id": "L-072",
    "title": "Internal Audit Checklist",
    "tags": ["audit", "controls", "compliance"],
}

_STATUSES = {"pass", "fail", "na"}


def _validate_internal_audit(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    checks = result.get("checks", [])
    totals = result.get("totals", {})
    pass_c = sum(1 for c in checks if c.get("status") == "pass")
    fail_c = sum(1 for c in checks if c.get("status") == "fail")
    na_c = sum(1 for c in checks if c.get("status") == "na")
    if int(totals.get("pass", 0) or 0) != pass_c:
        alerts.append("pass_totals_mismatch")
    if int(totals.get("fail", 0) or 0) != fail_c:
        alerts.append("fail_totals_mismatch")
    if int(totals.get("na", 0) or 0) != na_c:
        alerts.append("na_totals_mismatch")
    for c in checks:
        if c.get("status") not in _STATUSES:
            alerts.append("invalid_status")
    return alerts


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
        meta_url = f"{api_domain}/books/v3/settings?organization_id={org_id}"
        sources.append(meta_url)
        _ = get_json(meta_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "checks": [],
            "totals": {"pass": 0, "fail": 0, "na": 0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_internal_audit(result)
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
