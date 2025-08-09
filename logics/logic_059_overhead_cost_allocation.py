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
    "id": "L-059",
    "title": "Overhead Cost Allocation",
    "tags": ["overhead", "allocation", "manufacturing"],
}


def _validate_overhead_alloc(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    allocations = result.get("allocations", [])
    drivers = result.get("drivers", [])
    total_overhead = float(result.get("totals", {}).get("overhead", 0.0) or 0.0)
    sum_alloc = sum(float((a.get("allocated", 0.0) or 0.0)) for a in allocations)
    if abs(sum_alloc - total_overhead) > 0.01:
        alerts.append("allocations_do_not_sum_to_overhead")
    if any((d.get("base") or 0.0) < 0 for d in drivers):
        alerts.append("negative_driver_base")
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
        journals_url = f"{api_domain}/books/v3/journals?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.append(journals_url)
        _ = get_json(journals_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "drivers": [],
            "allocations": [],
            "totals": {"overhead": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_overhead_alloc(result)
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
