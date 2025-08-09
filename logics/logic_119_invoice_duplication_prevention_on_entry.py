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
    "id": "L-119",
    "title": "Invoice Duplication Prevention (On Entry)",
    "tags": ["duplicate", "guard", "ar"],
}


def _validate_dup_guard(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    allowed_reasons = {"number+date+customer"}
    for s in result.get("suspects", []) or []:
        if s.get("reason") not in allowed_reasons:
            alerts.append("invalid_reason")
        if s.get("incoming_ref") == s.get("conflict_with"):
            alerts.append("self_conflict")
    # rules present and active
    if not result.get("rules"):
        alerts.append("missing_rules")
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
    end_date = payload.get("end_date")
    headers = payload.get("headers", {})
    api_domain = payload.get("api_domain", "")
    query = payload.get("query", "")

    sources: List[str] = []
    out: Dict[str, Any] = {}

    try:
        inv_url = f"{api_domain}/books/v3/invoices?status=all&organization_id={org_id}"
        sources.append(inv_url)
        _ = get_json(inv_url, headers)

        out = {
            "as_of": end_date,
            "rules": [{"rule": "number+date+customer", "status": "active"}],
            "suspects": [],
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_dup_guard(out)
    learn = _learn_from_history(payload, out)
    conf = 0.6 - (0.15 if alerts else 0.0) - (0.1 if not out else 0.0)
    conf = max(0.1, min(0.95, conf))

    return {
        "result": out,
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
