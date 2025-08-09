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
    "id": "L-056",
    "title": "Inventory Valuation",
    "tags": ["inventory", "valuation", "stock"],
}


def _validate_inventory_valuation(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    items = result.get("items", [])
    total_val = float(result.get("totals", {}).get("value", 0.0) or 0.0)
    sum_val = 0.0
    for it in items:
        qty = float(it.get("qty", 0.0) or 0.0)
        rate = float(it.get("rate", 0.0) or 0.0)
        val = float(it.get("value", qty * rate))
        if abs(val - (qty * rate)) > 0.01:
            alerts.append(f"value_mismatch:{it.get('item','')}")
        if qty < 0:
            alerts.append(f"negative_qty:{it.get('item','')}")
        if rate < 0 or val < 0:
            alerts.append(f"negative_value:{it.get('item','')}")
        sum_val += val
    if abs(sum_val - total_val) > 0.01:
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
    end_date = payload.get("end_date")
    start_date = payload.get("start_date")
    headers = payload.get("headers", {})
    api_domain = payload.get("api_domain", "")
    query = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        stock_url = f"{api_domain}/books/v3/inventory/stockonhand?date_end={end_date}&organization_id={org_id}"
        sources.append(stock_url)
        _ = get_json(stock_url, headers)

        result = {
            "as_of": end_date,
            "items": [],
            "totals": {"value": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_inventory_valuation(result)
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
