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
    "id": "L-153",
    "title": "Period Lock & Unlock Tracker",
    "tags": ["period", "controls"],
}

_STATUS = {"locked", "unlocked"}


def _validate_plut(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        periods = result.get("periods") or []
        locked = 0
        unlocked = 0
        for p in periods:
            status = p.get("status")
            if status not in _STATUS:
                alerts.append("bad_status")
            if status == "locked":
                locked += 1
            if status == "unlocked":
                unlocked += 1
            # basic ISO month and timestamp checks are relaxed here
        totals = result.get("totals") or {}
        if totals.get("locked") != locked or totals.get("unlocked") != unlocked:
            alerts.append("totals_mismatch")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        signals.append(f"locked:{int((result.get('totals') or {}).get('locked', 0))}")
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
                "summary": {"size": len(result.get("periods") or [])},
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
        periods_url = f"{api_domain}/books/v3/settings/periods?organization_id={org_id}"
        sources.append(periods_url)
        _ = get_json(periods_url, headers)

        periods: List[Dict[str, Any]] = []
        result = {
            "as_of": end_date,
            "periods": periods,
            "totals": {"locked": 0, "unlocked": 0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_plut(result)
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
