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
    "id": "L-007",
    "title": "Material Purchase Summary",
    "tags": ["purchase", "materials", "items", "bills"],
}


def _validate_material_purchases(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        items = result.get("items", []) or []
        totals = result.get("totals", {}) or {}
        total_amount = float(totals.get("amount", 0) or 0)
        sum_amounts = 0.0
        for it in items:
            qty = float(it.get("qty", 0) or 0)
            amt = float(it.get("amount", 0) or 0)
            if qty < 0 or amt < 0:
                alerts.append("negative qty/amount")
                break
            sum_amounts += amt
        if abs(sum_amounts - total_amount) > 0.01:
            alerts.append("totals mismatch")
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
        sources.append("/books/v3/bills?date_start=&date_end=")
        sources.append("/books/v3/items")
        result = {
            "period": {"start_date": start_date, "end_date": end_date},
            "items": [],
            "totals": {"amount": 0.0},
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

    alerts = _validate_material_purchases(result)
    learn = _learn_from_history(payload, result)
    conf = 0.6
    if any(a in ("negative qty/amount", "totals mismatch") for a in alerts):
        conf -= 0.15
    if not result.get("items"):
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
