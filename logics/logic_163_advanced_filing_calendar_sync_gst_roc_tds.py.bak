"""
Title: Advanced Filing Calendar Sync Gst Roc Tds
ID: L-163
Tags: []
Required Inputs: schema://advanced_filing_calendar_sync_gst_roc_tds.input.v1
Outputs: schema://advanced_filing_calendar_sync_gst_roc_tds.output.v1
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
    "id": "L-163",
    "title": "Advanced Filing Calendar Sync (GST/ROC/TDS)",
    "tags": ["calendar", "filing", "due"],
}

_STATUS = {"filed", "pending", "overdue"}


def _validate_afc(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        evs = result.get("events") or []
        overdue = 0
        for e in evs:
            if e.get("status") not in _STATUS:
                alerts.append("bad_status")
            if e.get("status") == "overdue":
                overdue += 1
        totals = result.get("totals") or {}
        if totals.get("overdue") != overdue:
            alerts.append("totals_mismatch")
        if overdue > 0:
            alerts.append("overdue_present")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], _alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        signals.append(f"overdue:{int((result.get('totals') or {}).get('overdue', 0))}")
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
                "summary": {"size": len(result.get("events") or [])},
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
        cal_url = f"{api_domain}/books/v3/filings/calendar?organization_id={org_id}"
        sources.append(cal_url)
        _ = get_json(cal_url, headers)

        events: List[Dict[str, Any]] = []
        result = {
            "as_of": end_date,
            "events": events,
            "totals": {"overdue": 0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_afc(result)
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
