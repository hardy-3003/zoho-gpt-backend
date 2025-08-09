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
    "id": "L-105",
    "title": "BOQ vs Actual Cost",
    "tags": ["boq", "actual", "variance", "projects"],
}


def _validate_boq_actual(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    items = result.get("items", [])
    totals = result.get("totals", {})
    sum_boq = sum(float((x.get("boq_cost", 0.0) or 0.0)) for x in items)
    sum_actual = sum(float((x.get("actual_cost", 0.0) or 0.0)) for x in items)
    sum_var = sum(
        float(
            (
                x.get("variance", 0.0)
                or (x.get("actual_cost", 0.0) or 0.0) - (x.get("boq_cost", 0.0) or 0.0)
            )
        )
        for x in items
    )
    if abs(sum_boq - float(totals.get("boq_cost", 0.0) or 0.0)) > 0.01:
        alerts.append("totals_boq_mismatch")
    if abs(sum_actual - float(totals.get("actual_cost", 0.0) or 0.0)) > 0.01:
        alerts.append("totals_actual_mismatch")
    if abs(sum_var - float(totals.get("variance", 0.0) or 0.0)) > 0.01:
        alerts.append("totals_variance_mismatch")
    for it in items:
        boq = float(it.get("boq_cost", 0.0) or 0.0)
        act = float(it.get("actual_cost", 0.0) or 0.0)
        var = float(it.get("variance", act - boq))
        pct = it.get("variance_pct")
        if abs(var - (act - boq)) > 0.01:
            alerts.append(f"variance_math_error:{it.get('boq_item','')}")
        if pct is not None and (pct < -1000 or pct > 1000):
            alerts.append(f"variance_pct_out_of_bounds:{it.get('boq_item','')}")
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
        sources.extend([bills_url, journals_url])
        _ = get_json(bills_url, headers)
        _ = get_json(journals_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "items": [],
            "totals": {"boq_cost": 0.0, "actual_cost": 0.0, "variance": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_boq_actual(result)
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
