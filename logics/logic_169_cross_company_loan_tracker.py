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
    "id": "L-169",
    "title": "Cross-company Loan Tracker",
    "tags": ["intercompany", "loan", "treasury"],
}


def _validate_cclt(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    loans = result.get("loans") or []
    exposure = float((result.get("totals") or {}).get("net_exposure", 0.0) or 0.0)
    agg = 0.0
    for l in loans:
        f, t = (l.get("from") or ""), (l.get("to") or "")
        if f == t:
            alerts.append("same_counterparty")
        opening = float(l.get("opening", 0.0) or 0.0)
        inflow = float(l.get("inflow", 0.0) or 0.0)
        outflow = float(l.get("outflow", 0.0) or 0.0)
        closing = float(l.get("closing", 0.0) or 0.0)
        if round(opening + inflow - outflow, 2) != round(closing, 2):
            alerts.append("closing_mismatch")
        agg += closing
    if round(agg, 2) != round(exposure, 2):
        alerts.append("exposure_mismatch")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        net = float((result.get("totals") or {}).get("net_exposure") or 0.0)
        band = "pos" if net > 0 else ("neg" if net < 0 else "zero")
        signals.append(f"exposure:{band}")
        active = sum(
            1 for l in (result.get("loans") or []) if l.get("status") == "active"
        )
        signals.append(f"active:{active}")
        if alerts:
            signals.append("alert:present")
    except Exception:
        pass
    try:
        append_event(
            LOGIC_META["id"],
            {
                "org_id": payload.get("org_id"),
                "period": {
                    "start": payload.get("start_date"),
                    "end": payload.get("end_date"),
                },
                "signals": signals,
            },
        )
    except Exception:
        pass
    return {"notes": signals[:3]}


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
        loans: List[Dict[str, Any]] = []
        # Deterministic empty baseline; totals must reconcile
        net_exposure = round(sum(float(l.get("closing") or 0.0) for l in loans), 2)
        result = {
            "period": {"start": start_date, "end": end_date},
            "loans": loans,
            "totals": {"net_exposure": net_exposure},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_cclt(result)
    learn = _learn_from_history(payload, result, alerts)
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
