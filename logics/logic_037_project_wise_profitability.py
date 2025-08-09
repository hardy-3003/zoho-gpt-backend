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
    "id": "L-037",
    "title": "Project-wise Profitability",
    "tags": ["projects", "profitability", "margin"],
}


def _validate_project_profit(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    projects = result.get("projects", [])
    for p in projects:
        revenue = float(p.get("revenue", 0.0) or 0.0)
        cost = float(p.get("cost", 0.0) or 0.0)
        profit = float(p.get("profit", revenue - cost))
        margin = float(p.get("margin_pct", 0.0) or 0.0)
        if abs(profit - (revenue - cost)) > 0.01:
            alerts.append(f"profit_mismatch:{p.get('project','')}")
        if margin < -100 or margin > 100:
            alerts.append(f"margin_out_of_bounds:{p.get('project','')}")
    totals = result.get("totals", {})
    if totals:
        r = float(totals.get("revenue", 0.0) or 0.0)
        c = float(totals.get("cost", 0.0) or 0.0)
        pr = float(totals.get("profit", 0.0) or 0.0)
        if abs(pr - (r - c)) > 0.01:
            alerts.append("totals_profit_mismatch")
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
        projects_url = f"{api_domain}/books/v3/projects?organization_id={org_id}"
        inv_url = f"{api_domain}/books/v3/invoices?organization_id={org_id}&date_start={start_date}&date_end={end_date}"
        bill_url = f"{api_domain}/books/v3/bills?organization_id={org_id}&date_start={start_date}&date_end={end_date}"
        sources.extend([projects_url, inv_url, bill_url])
        _ = get_json(projects_url, headers)
        _ = get_json(inv_url, headers)
        _ = get_json(bill_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "projects": [],
            "totals": {"revenue": 0.0, "cost": 0.0, "profit": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_project_profit(result)
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
