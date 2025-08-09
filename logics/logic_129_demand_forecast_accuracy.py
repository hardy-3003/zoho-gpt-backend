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
    "id": "L-129",
    "title": "Demand Forecast Accuracy (MAPE)",
    "tags": ["forecast", "accuracy", "planning"],
}


def _validate_mape(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        mape = result.get("mape_pct")
        if mape is not None:
            m = float(mape)
            if m < 0 or m > 100:
                alerts.append("mape_out_of_bounds")
        for row in result.get("series", []) or []:
            ape = row.get("ape_pct")
            forecast = row.get("forecast")
            if ape is None and forecast is not None:
                alerts.append("ape_missing_with_forecast")
    except Exception:
        alerts.append("invalid_series")
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
        actuals_url = f"{api_domain}/books/v3/invoices?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        forecasts_url = f"{api_domain}/books/v3/custom/forecasts?period={start_date}:{end_date}&organization_id={org_id}"
        sources.extend([actuals_url, forecasts_url])

        _ = get_json(actuals_url, headers)
        _ = get_json(forecasts_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "mape_pct": None,
            "series": [],
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_mape(result)
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
