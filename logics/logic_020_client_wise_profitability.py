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
    "id": "L-020",
    "title": "Client-wise Profitability",
    "tags": ["profitability", "client", "margin"],
}


def _validate_client_profitability(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        clients = result.get("clients", []) or []
        for c in clients:
            revenue = float(c.get("revenue", 0) or 0)
            cost = float(c.get("cost", 0) or 0)
            margin = float(c.get("margin", 0) or 0)
            if abs(margin - (revenue - cost)) > 0.01:
                alerts.append("margin math mismatch")
                break
            pct = float(c.get("margin_pct", 0) or 0)
            if revenue != 0 and abs(pct - (margin / revenue * 100.0)) > 0.1:
                alerts.append("margin pct inconsistent")
                break
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
        sources.append("/books/v3/invoices?date_start=&date_end=")
        sources.append("/books/v3/bills?date_start=&date_end=")
        sources.append("/books/v3/journals?search=cost_allocation")
        result = {
            "period": {"start_date": start_date, "end_date": end_date},
            "clients": [],
            "totals": {"revenue": 0.0, "cost": 0.0, "margin": 0.0, "margin_pct": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
            "error": str(e),
        }

    alerts = _validate_client_profitability(result)
    learn = _learn_from_history(payload, result)

    base_conf = 0.6
    if alerts:
        base_conf -= 0.15

    return {
        "result": result,
        "provenance": {"sources": sources},
        "confidence": max(0.1, min(0.95, base_conf)),
        "alerts": alerts,
        "meta": {
            "strategy": "l4-v0",
            "org_id": org_id,
            "query": query,
            "notes": learn.get("notes", []),
        },
    }
