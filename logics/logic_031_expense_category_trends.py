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
    "id": "L-031",
    "title": "Expense Category Trends",
    "tags": ["expenses", "trend", "categories", "finance"],
}


def _validate_expense_trends(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    categories = result.get("categories", [])
    totals_amount = float(result.get("totals", {}).get("amount", 0.0) or 0.0)
    sum_amount = sum(float((c.get("amount", 0.0) or 0.0)) for c in categories)
    if abs(totals_amount - sum_amount) > 0.01:
        alerts.append("totals_mismatch")
    for c in categories:
        amt = float(c.get("amount", 0.0) or 0.0)
        mom = c.get("mom_pct")
        if amt < 0:
            alerts.append(f"negative_amount:{c.get('category','')}")
        if mom is not None and abs(float(mom)) > 50.0:
            alerts.append(f"high_volatility:{c.get('category','')}")
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
        bills_url = f"{api_domain}/books/v3/bills?date_start={start_date}&date_end={end_date}&include_line_items=true&organization_id={org_id}"
        coa_url = f"{api_domain}/books/v3/chartofaccounts?organization_id={org_id}"
        sources.extend([bills_url, coa_url])
        _ = get_json(bills_url, headers)
        _ = get_json(coa_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "categories": [],
            "totals": {"amount": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_expense_trends(result)
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
