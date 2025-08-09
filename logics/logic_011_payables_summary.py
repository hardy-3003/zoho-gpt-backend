from typing import Dict, Any, List

# Prefer helpers; define safe fallbacks to keep imports working in all envs
try:  # noqa: F401 - imported for side-effect/use when present
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

    except Exception:  # pragma: no cover

        def append_event(_logic_id: str, _data: Dict[str, Any]) -> None:  # type: ignore
            return None


LOGIC_META = {
    "id": "L-011",
    "title": "Payables Summary",
    "tags": ["payables", "ap", "creditors", "bills", "outstanding"],
}


def _validate_payables(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        vendors: List[Dict[str, Any]] = result.get("vendors", []) or []
        totals = result.get("totals", {}) or {}
        total_billed = float(totals.get("billed", 0) or 0)
        total_paid = float(totals.get("paid", 0) or 0)
        total_out = float(totals.get("outstanding", 0) or 0)
        if abs(total_billed - (total_paid + total_out)) > 0.01:
            alerts.append("unbalanced totals: billed != paid+outstanding")
        if any(
            float(v.get("billed", 0) or 0) < 0
            or float(v.get("paid", 0) or 0) < 0
            or float(v.get("outstanding", 0) or 0) < 0
            for v in vendors
        ):
            alerts.append("negative amount detected")
        if total_out > 0:
            for v in vendors:
                share = float(v.get("outstanding", 0) or 0) / total_out
                if share > 0.6:
                    alerts.append("vendor outstanding concentration >60%")
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
        # Sources used for this summary
        sources.append("/books/v3/bills?date_start=&date_end=")
        sources.append("/books/v3/vendorpayments?date_start=&date_end=")

        # Deterministic placeholder aggregation
        result = {
            "period": {"start_date": start_date, "end_date": end_date},
            "vendors": [],
            "totals": {"billed": 0.0, "paid": 0.0, "outstanding": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_payables(result)
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
