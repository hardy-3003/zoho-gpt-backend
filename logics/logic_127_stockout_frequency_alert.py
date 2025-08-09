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
    "id": "L-127",
    "title": "Stockout Frequency Alert",
    "tags": ["stockout", "inventory", "alert"],
}


def _validate_stockout(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    warn = (result.get("thresholds") or {}).get("occurrences_warn", 1)
    for row in result.get("alerts", []) or []:
        try:
            occ = int(row.get("occurrences", 0))
            if occ < 0:
                alerts.append("negative_occurrences")
            if occ > int(warn):
                alerts.append("stockout_exceeds_threshold")
        except Exception:
            alerts.append("invalid_occurrence_value")
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
        tx_issue_url = f"{api_domain}/books/v3/inventory/transactions?date_start={start_date}&date_end={end_date}&type=issue&organization_id={org_id}"
        tx_sale_url = f"{api_domain}/books/v3/inventory/transactions?date_start={start_date}&date_end={end_date}&type=sale&organization_id={org_id}"
        sources.extend([items_url, stock_url, tx_issue_url, tx_sale_url])

        _ = get_json(items_url, headers)
        _ = get_json(stock_url, headers)
        _ = get_json(tx_issue_url, headers)
        _ = get_json(tx_sale_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "alerts": [],
            "thresholds": {"occurrences_warn": 1},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_stockout(result)
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
