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
    "id": "L-117",
    "title": "Multi-GSTIN Entity Aggregator",
    "tags": ["gstin", "multi-entity", "consolidation"],
}


def _validate_multi_gstin(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    total_r = float(result.get("totals", {}).get("revenue", 0.0) or 0.0)
    total_e = float(result.get("totals", {}).get("expense", 0.0) or 0.0)
    total_p = float(result.get("totals", {}).get("profit", 0.0) or 0.0)
    sum_r = sum(
        float(x.get("revenue", 0.0) or 0.0) for x in result.get("entities", []) or []
    )
    sum_e = sum(
        float(x.get("expense", 0.0) or 0.0) for x in result.get("entities", []) or []
    )
    sum_p = sum(
        float(x.get("profit", 0.0) or 0.0) for x in result.get("entities", []) or []
    )
    if (
        abs(sum_r - total_r) > 0.01
        or abs(sum_e - total_e) > 0.01
        or abs(sum_p - total_p) > 0.01
    ):
        alerts.append("totals_mismatch")
    if any(
        float(x.get("revenue", 0.0) or 0.0) < 0.0
        for x in result.get("entities", []) or []
    ):
        alerts.append("negative_revenue")
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
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    headers = payload.get("headers", {})
    api_domain = payload.get("api_domain", "")
    query = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        ent_url = f"{api_domain}/books/v3/organization/gstins?organization_id={org_id}"
        inv_url = f"{api_domain}/books/v3/invoices?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        bill_url = f"{api_domain}/books/v3/bills?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.extend([ent_url, inv_url, bill_url])
        _ = get_json(ent_url, headers)
        _ = get_json(inv_url, headers)
        _ = get_json(bill_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "entities": [],
            "totals": {"revenue": 0.0, "expense": 0.0, "profit": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_multi_gstin(result)
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
