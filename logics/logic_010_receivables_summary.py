from typing import Dict, Any, List

try:  # noqa: F401
    from helpers.zoho_client import get_json  # type: ignore
except Exception:  # pragma: no cover

    def get_json(_url: str, headers: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore
        return {}


try:
    from helpers.history_store import append_event  # type: ignore
except Exception:  # pragma: no cover
    try:
        from helpers.history_store import write_event as _write_event  # type: ignore

        def append_event(logic_id: str, data: Dict[str, Any]) -> None:  # type: ignore
            _write_event(f"logic_{logic_id}", data)

    except Exception:

        def append_event(_logic_id: str, _data: Dict[str, Any]) -> None:  # type: ignore
            return None


LOGIC_META = {
    "id": "L-010",
    "title": "Receivables Summary",
    "tags": ["receivables", "debtors", "aging", "ar"],
}


def _validate_receivables_summary(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        aging = result.get("aging", {}) or {}
        total_unpaid = float(result.get("totals", {}).get("unpaid", 0) or 0)
        sum_bins = sum(
            float(aging.get(k, 0) or 0)
            for k in ["0-30", "31-60", "61-90", "91-180", "180+"]
        )
        if abs(sum_bins - total_unpaid) > 0.01:
            alerts.append("totals mismatch")
        if total_unpaid > 0:
            if (
                float(aging.get("91-180", 0) or 0) + float(aging.get("180+", 0) or 0)
            ) / total_unpaid > 0.25:
                alerts.append("90+ share >25%")
    except Exception:
        alerts.append("validation error")
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
    headers: Dict[str, Any] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        sources.append("/books/v3/invoices?status=unpaid&date_end=")
        result = {
            "as_of": end_date,
            "aging": {
                "0-30": 0.0,
                "31-60": 0.0,
                "61-90": 0.0,
                "91-180": 0.0,
                "180+": 0.0,
            },
            "top_debtors": [],
            "totals": {"unpaid": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_receivables_summary(result)
    learn = _learn_from_history(payload, result)
    conf = 0.6
    if any(a in ("totals mismatch", "90+ share >25%") for a in alerts):
        conf -= 0.15
    if result.get("totals", {}).get("unpaid", 0) == 0:
        conf -= 0.10
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
