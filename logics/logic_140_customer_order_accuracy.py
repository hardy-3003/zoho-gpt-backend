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
    "id": "L-140",
    "title": "Customer Order Accuracy",
    "tags": ["order", "accuracy", "customers"],
}


def _validate_accuracy(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        ap = result.get("accuracy_pct")
        if ap is not None:
            a = float(ap)
            if a < 0 or a > 100:
                alerts.append("accuracy_out_of_bounds")
        basis = result.get("basis") or {}
        tot = int(basis.get("total_orders", 0))
        err = int(basis.get("errors", 0))
        if tot < 0 or err < 0:
            alerts.append("invalid_basis")
        if tot > 0 and ap is not None:
            expected = (1.0 - (err / float(tot))) * 100.0
            if abs(float(ap) - expected) > 0.0001:
                alerts.append("accuracy_mismatch")
    except Exception:
        alerts.append("invalid_result")
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
        inv_url = f"{api_domain}/books/v3/invoices?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        ret_url = f"{api_domain}/books/v3/creditnotes?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.extend([inv_url, ret_url])

        _ = get_json(inv_url, headers)
        _ = get_json(ret_url, headers)

        res = {
            "period": {"start": start_date, "end": end_date},
            "accuracy_pct": None,
            "basis": {"total_orders": 0, "errors": 0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_accuracy(res)
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
