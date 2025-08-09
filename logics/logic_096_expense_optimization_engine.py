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
    "id": "L-096",
    "title": "Expense Optimization Engine",
    "tags": ["optimization", "cost", "savings"],
}


def _validate_expense_opt(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    total = float(result.get("totals", {}).get("savings", 0.0) or 0.0)
    sum_sav = 0.0
    for o in result.get("opportunities", []):
        cur = float(o.get("current", 0.0) or 0.0)
        tgt = float(o.get("target", 0.0) or 0.0)
        sav = float(o.get("savings", 0.0) or 0.0)
        if cur < 0 or tgt < 0 or sav < 0:
            alerts.append("negative_values")
        if abs((cur - tgt) - sav) > 0.01:
            alerts.append("savings_mismatch")
        sum_sav += sav
    if abs(sum_sav - total) > 0.01:
        alerts.append("totals_mismatch")
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
        bills_url = f"{api_domain}/books/v3/bills?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.append(bills_url)
        _ = get_json(bills_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "opportunities": [],
            "totals": {"savings": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_expense_opt(result)
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
