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
    "id": "L-143",
    "title": "Fleet Utilization Rate",
    "tags": ["fleet", "utilization", "transport"],
}


def _validate_fleet(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        up = result.get("utilization_pct")
        if up is not None:
            u = float(up)
            if u < 0 or u > 100:
                alerts.append("utilization_out_of_bounds")
        for v in result.get("vehicles", []) or []:
            vp = v.get("utilization_pct")
            if vp is not None:
                val = float(vp)
                if val < 0 or val > 100:
                    alerts.append("vehicle_utilization_out_of_bounds")
    except Exception:
        alerts.append("invalid_vehicles")
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
    res: Dict[str, Any] = {}

    try:
        vehicles_url = f"{api_domain}/books/v3/fleet/vehicles?organization_id={org_id}"
        trips_url = f"{api_domain}/books/v3/fleet/trips?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.extend([vehicles_url, trips_url])

        _ = get_json(vehicles_url, headers)
        _ = get_json(trips_url, headers)

        res = {
            "period": {"start": start_date, "end": end_date},
            "utilization_pct": None,
            "vehicles": [],
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_fleet(res)
    learn = _learn_from_history(payload, res)
    conf = 0.6 - (0.15 if alerts else 0.0) - (0.1 if not res else 0.0)
    conf = max(0.1, min(0.95, conf))

    return {
        "result": res,
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
