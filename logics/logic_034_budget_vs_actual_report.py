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
    "id": "L-034",
    "title": "Budget vs Actual",
    "tags": ["budget", "actual", "variance", "finance"],
}


def _validate_budget_actual(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    lines = result.get("lines", [])
    for ln in lines:
        budget = float(ln.get("budget", 0.0) or 0.0)
        actual = float(ln.get("actual", 0.0) or 0.0)
        variance = float(ln.get("variance", actual - budget))
        pct = float(ln.get("variance_pct", 0.0) or 0.0)
        if abs(variance - (actual - budget)) > 0.01:
            alerts.append(f"variance_mismatch:{ln.get('account','')}")
        if pct < -1000 or pct > 1000:
            alerts.append(f"variance_pct_out_of_bounds:{ln.get('account','')}")
    totals = result.get("totals", {})
    if totals:
        b = float(totals.get("budget", 0.0) or 0.0)
        a = float(totals.get("actual", 0.0) or 0.0)
        v = float(totals.get("variance", 0.0) or 0.0)
        if abs(v - (a - b)) > 0.01:
            alerts.append("totals_variance_mismatch")
        pct = float(totals.get("variance_pct", 0.0) or 0.0)
        if pct < -1000 or pct > 1000:
            alerts.append("totals_variance_pct_out_of_bounds")
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
        budgets_url = f"{api_domain}/books/v3/budgets?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        journals_url = f"{api_domain}/books/v3/journals?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.extend([budgets_url, journals_url])
        _ = get_json(budgets_url, headers)
        _ = get_json(journals_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "lines": [],
            "totals": {
                "budget": 0.0,
                "actual": 0.0,
                "variance": 0.0,
                "variance_pct": 0.0,
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

    alerts = _validate_budget_actual(result)
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
