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
    "id": "L-160",
    "title": "User Access Logs & Abuse Detection",
    "tags": ["access", "abuse", "security"],
}

_RISK = {"low", "med", "high"}


def _validate_uaad(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        events = result.get("events") or []
        high = 0
        for e in events:
            if e.get("risk") not in _RISK:
                alerts.append("bad_risk")
            if e.get("risk") == "high":
                high += 1
        totals = result.get("totals") or {}
        if totals.get("count") != len(events) or totals.get("high") != high:
            alerts.append("totals_mismatch")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts_list: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        signals.append(f"risk_high:{int((result.get('totals') or {}).get('high', 0))}")
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
    org_id: Optional[str] = payload.get("org_id")
    start_date: Optional[str] = payload.get("start_date")
    end_date: Optional[str] = payload.get("end_date")
    headers: Dict[str, str] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        sources.append("/books/v3/audit/accesslogs")
        _ = get_json(
            f"{api_domain}/books/v3/audit/accesslogs?date_start={start_date}&date_end={end_date}&organization_id={org_id}",
            headers,
        )

        events: List[Dict[str, Any]] = []
        result = {
            "period": {"start": start_date, "end": end_date},
            "events": events,
            "totals": {"count": len(events), "high": 0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_uaad(result)
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
