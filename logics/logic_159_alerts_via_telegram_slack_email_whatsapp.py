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
    "id": "L-159",
    "title": "Alerts via Telegram/Slack/Email/WhatsApp",
    "tags": ["alerts", "notify", "channels"],
}

_CHANNELS = {"slack", "telegram", "email", "whatsapp"}
_STATUS = {"configured", "missing"}


def _validate_alerts(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        chs = result.get("channels") or []
        conf = 0
        miss = 0
        for c in chs:
            if c.get("channel") not in _CHANNELS:
                alerts.append("bad_channel")
            if c.get("status") not in _STATUS:
                alerts.append("bad_status")
            if c.get("status") == "configured":
                conf += 1
            if c.get("status") == "missing":
                miss += 1
        totals = result.get("totals") or {}
        if totals.get("configured") != conf or totals.get("missing") != miss:
            alerts.append("totals_mismatch")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts_list: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        miss = int((result.get("totals") or {}).get("missing", 0))
        signals.append("channels:ok" if miss == 0 else "channels:missing")
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
                "summary": {"size": len(result.get("channels") or [])},
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
        sources.append("/books/v3/alerts/channels")
        _ = get_json(f"{api_domain}/books/v3/alerts?organization_id={org_id}", headers)

        channels: List[Dict[str, Any]] = []
        result = {
            "as_of": end_date,
            "channels": channels,
            "totals": {"configured": 0, "missing": 0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_alerts(result)
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
