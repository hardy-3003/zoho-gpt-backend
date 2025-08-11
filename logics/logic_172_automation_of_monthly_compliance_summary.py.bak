"""
Title: Automation Of Monthly Compliance Summary
ID: L-172
Tags: []
Required Inputs: schema://automation_of_monthly_compliance_summary.input.v1
Outputs: schema://automation_of_monthly_compliance_summary.output.v1
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
    "id": "L-172",
    "title": "Automation of Monthly Compliance Summary",
    "tags": ["automation", "compliance"],
}


def _validate_amcs(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    forms = result.get("forms") or []
    counts = {"filed": 0, "pending": 0, "overdue": 0}
    valid_status = {"filed", "pending", "overdue"}
    for f in forms:
        st = f.get("status")
        if st not in valid_status:
            alerts.append("invalid_status")
        else:
            counts[st] += 1
    totals = result.get("totals") or {}
    for k, v in counts.items():
        if int(totals.get(k, -1)) != v:
            alerts.append("totals_mismatch")
            break
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        overdue = int((result.get("totals") or {}).get("overdue", 0))
        signals.append(f"overdue:{overdue}")
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
        # Deterministic placeholder of forms; no external calls
        forms: List[Dict[str, Any]] = []
        totals = {"filed": 0, "pending": 0, "overdue": 0}
        for f in forms:
            if f.get("status") in totals:
                totals[f["status"]] += 1
        result = {
            "period": {"start": start_date, "end": end_date},
            "forms": forms,
            "totals": totals,
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_amcs(result)
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
