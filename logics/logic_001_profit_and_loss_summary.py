from typing import Dict, Any, List

# Prefer using helpers if available; define safe fallbacks to keep imports clean
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
    "id": "L-001",
    "title": "Profit & Loss Summary",
    "tags": ["pnl", "profit", "loss", "summary", "income", "expense", "finance"],
}


def _validate_pnl_summary(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        totals = result.get("totals", {})
        income_total = float(totals.get("income_total", 0) or 0)
        expense_total = float(totals.get("expense_total", 0) or 0)
        profit = float(totals.get("profit", 0) or 0)
        if abs(income_total - expense_total - profit) > 0.01:
            alerts.append("unbalanced: income - expense != profit")
        breakdown = result.get("breakdown", {}) or {}
        income_lines = breakdown.get("Income", []) or []
        expense_lines = breakdown.get("Expenses", []) or []
        if not income_lines and not expense_lines:
            alerts.append("empty breakdown")
        for line in income_lines + expense_lines:
            amt = float(line.get("amount", 0) or 0)
            if amt < 0:
                alerts.append("negative amount detected")
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
    org_id: Any = payload.get("org_id")
    start_date: Any = payload.get("start_date")
    end_date: Any = payload.get("end_date")
    headers: Dict[str, Any] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        # Deterministic placeholder without external calls
        # Document intended sources
        sources.append("/books/v3/invoices?date_start=&date_end=")
        sources.append("/books/v3/bills?date_start=&date_end=")

        result = {
            "period": {"start_date": start_date, "end_date": end_date},
            "totals": {"income_total": 0.0, "expense_total": 0.0, "profit": 0.0},
            "breakdown": {"Income": [], "Expenses": []},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_pnl_summary(result)
    learn = _learn_from_history(payload, result)

    conf = 0.6
    if any(a.startswith("unbalanced") for a in alerts):
        conf -= 0.15
    if "empty breakdown" in alerts:
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
# ---- L4 wrapper glue (safe, additive) ----------------------------------------
try:
    from helpers.logic_contract import l4_compliant
except Exception:  # fallback if import fails
    def l4_compliant(*_a, **_k):
        def _wrap(f): return f
        return _wrap

# Resolve the underlying implementation once, in this order
_handle_impl = None
for _name in ("handle_impl", "handle_core", "handle"):
    if _name in globals() and callable(globals()[_name]):
        _handle_impl = globals()[_name]
        break

@l4_compliant(validate=True, logic_id="L-001")
def handle(payload):
    if _handle_impl is None:
        # Standard error envelope if the file had no implementation
        return {
            "result": None,
            "provenance": {"source": "internal", "path": None},
            "confidence": 0.2,
            "alerts": [{"level": "error", "message": "No underlying handle implementation found"}],
            "meta": {"logic": "L-001"}
        }
    return _handle_impl(payload)
# ------------------------------------------------------------------------------
