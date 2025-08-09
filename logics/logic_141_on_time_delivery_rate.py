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
    "id": "L-141",
    "title": "On-time Delivery Rate",
    "tags": ["delivery", "on-time", "logistics"],
}


def _validate_ontime(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        otp = result.get("on_time_pct")
        if otp is not None:
            o = float(otp)
            if o < 0 or o > 100:
                alerts.append("ontime_out_of_bounds")
        for r in result.get("routes", []) or []:
            p = r.get("on_time_pct")
            if p is not None:
                v = float(p)
                if v < 0 or v > 100:
                    alerts.append("route_otp_out_of_bounds")
                if v < 85:
                    alerts.append("route_otp_below_threshold")
    except Exception:
        alerts.append("invalid_routes")
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
        ship_url = f"{api_domain}/books/v3/shipments?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        so_url = f"{api_domain}/books/v3/salesorders?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.extend([ship_url, so_url])

        _ = get_json(ship_url, headers)
        _ = get_json(so_url, headers)

        res = {
            "period": {"start": start_date, "end": end_date},
            "on_time_pct": None,
            "routes": [],
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_ontime(res)
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
