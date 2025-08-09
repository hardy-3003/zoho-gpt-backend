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
    "id": "L-064",
    "title": "Client Acquisition Cost",
    "tags": ["cac", "marketing", "sales"],
}


def _validate_cac(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    comps = result.get("components", {})
    marketing = float(comps.get("marketing", 0.0) or 0.0)
    sales = float(comps.get("sales", 0.0) or 0.0)
    new_clients = int(comps.get("new_clients", 0) or 0)
    cac = result.get("cac")
    if new_clients > 0:
        expected = (marketing + sales) / new_clients
        if cac is not None and abs(float(cac) - expected) > 0.01:
            alerts.append("cac_mismatch")
    else:
        if cac is not None:
            alerts.append("cac_should_be_null_when_no_new_clients")
    if marketing < 0 or sales < 0:
        alerts.append("negative_component")
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
        journals_url = f"{api_domain}/books/v3/journals?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        customers_url = f"{api_domain}/books/v3/customers?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.extend([bills_url, journals_url, customers_url])
        _ = get_json(bills_url, headers)
        _ = get_json(journals_url, headers)
        _ = get_json(customers_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "cac": None,
            "components": {"marketing": 0.0, "sales": 0.0, "new_clients": 0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_cac(result)
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
