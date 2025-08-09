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
    "id": "L-154",
    "title": "Custom Rule Builder (SaaS)",
    "tags": ["rules", "saas", "validation"],
}

_SCOPES = {"ar", "ap", "je", "inventory"}
_STATUS = {"active", "inactive"}


def _validate_crb(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        rules = result.get("rules") or []
        active = 0
        inactive = 0
        for r in rules:
            if r.get("scope") not in _SCOPES:
                alerts.append("bad_scope")
            if r.get("status") not in _STATUS:
                alerts.append("bad_status")
            if r.get("status") == "active":
                active += 1
            if r.get("status") == "inactive":
                inactive += 1
            if not r.get("expr"):
                alerts.append("empty_expr")
        totals = result.get("totals") or {}
        if totals.get("active") != active or totals.get("inactive") != inactive:
            alerts.append("totals_mismatch")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        signals.append(
            f"rules_active:{int((result.get('totals') or {}).get('active', 0))}"
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
                "summary": {"size": len(result.get("rules") or [])},
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
        rules_url = f"{api_domain}/books/v3/customrules?organization_id={org_id}"
        sources.append(rules_url)
        _ = get_json(rules_url, headers)

        rules: List[Dict[str, Any]] = []
        result = {
            "as_of": end_date,
            "rules": rules,
            "totals": {"active": 0, "inactive": 0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_crb(result)
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
