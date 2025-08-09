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
    "id": "L-131",
    "title": "Supplier Lead Time Variability",
    "tags": ["supplier", "lead-time", "variability"],
}


def _validate_leadtime(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        for sp in result.get("suppliers", []) or []:
            orders = int(sp.get("orders", 0))
            stdv = float(sp.get("std_dev_days", 0.0))
            avg = float(sp.get("avg_days", 0.0))
            if orders < 0 or stdv < 0:
                alerts.append("invalid_supplier_values")
            if avg > 7.0 or stdv > 5.0:
                alerts.append("lead_time_exceeds_threshold")
    except Exception:
        alerts.append("invalid_suppliers")
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
        po_url = f"{api_domain}/books/v3/purchaseorders?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        bills_url = f"{api_domain}/books/v3/bills?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.extend([po_url, bills_url])

        _ = get_json(po_url, headers)
        _ = get_json(bills_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "suppliers": [],
            "totals": {"suppliers": 0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_leadtime(result)
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
