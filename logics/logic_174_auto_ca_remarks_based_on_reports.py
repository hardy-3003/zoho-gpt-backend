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
    "id": "L-174",
    "title": "Auto CA Remarks Based on Reports",
    "tags": ["remarks", "ca", "summary"],
}


def _validate_acar(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    remarks = result.get("remarks") or []
    valid = {"info", "warn", "critical"}
    critical_count = 0
    for r in remarks:
        if r.get("severity") not in valid:
            alerts.append("invalid_severity")
        if r.get("severity") == "critical":
            critical_count += 1
    totals = result.get("totals") or {}
    if int(totals.get("critical", 0)) != critical_count:
        alerts.append("critical_count_mismatch")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        remarks = result.get("remarks") or []
        crit = sum(1 for r in remarks if r.get("severity") == "critical")
        signals.append(f"critical:{crit}")
        top_topic = remarks[0]["topic"] if remarks else "na"
        signals.append(f"top_topic:{top_topic}")
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
        remarks: List[Dict[str, Any]] = []
        result = {
            "period": {"start": start_date, "end": end_date},
            "remarks": remarks,
            "totals": {
                "critical": sum(1 for r in remarks if r.get("severity") == "critical")
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

    alerts = _validate_acar(result)
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
