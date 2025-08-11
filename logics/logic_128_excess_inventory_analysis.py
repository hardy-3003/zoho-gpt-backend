"""
Title: Excess Inventory Analysis
ID: L-128
Tags: []
Required Inputs: schema://excess_inventory_analysis.input.v1
Outputs: schema://excess_inventory_analysis.output.v1
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
    "id": "L-128",
    "title": "Excess Inventory Analysis",
    "tags": ["inventory", "excess", "holding-cost"],
}


def _validate_excess(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    threshold_days = (result.get("assumptions") or {}).get("excess_threshold_days", 180)
    for it in result.get("items", []) or []:
        try:
            doh = float(it.get("days_on_hand", 0.0))
            val = float(it.get("value", 0.0))
            if doh < 0 or val < 0:
                alerts.append("invalid_values")
            if doh > float(threshold_days):
                alerts.append("excess_days_on_hand")
        except Exception:
            alerts.append("invalid_item")
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
    org_id: Optional[str] = payload.get("org_id")
    start_date: Optional[str] = payload.get("start_date")
    end_date: Optional[str] = payload.get("end_date")
    headers: Dict[str, str] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        items_url = f"{api_domain}/books/v3/items?organization_id={org_id}"
        stock_url = f"{api_domain}/books/v3/inventory/stockonhand?date_end={end_date}&organization_id={org_id}"
        # Example per-item usage estimation source (stub by item filter)
        invoices_url = f"{api_domain}/books/v3/invoices?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.extend([items_url, stock_url, invoices_url])

        _ = get_json(items_url, headers)
        _ = get_json(stock_url, headers)
        _ = get_json(invoices_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "items": [],
            "totals": {"items": 0, "value": 0.0},
            "assumptions": {"excess_threshold_days": 180},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_excess(result)
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
