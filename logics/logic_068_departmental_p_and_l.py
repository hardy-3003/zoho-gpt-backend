"""
Title: Departmental P And L
ID: L-068
Tags: []
Required Inputs: schema://departmental_p_and_l.input.v1
Outputs: schema://departmental_p_and_l.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only.
"""
from typing import Dict, Any, List

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
    "id": "L-068",
    "title": "Departmental P&L",
    "tags": ["department", "pnl", "profitability"],
}


def _validate_dept_pnl(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    depts = result.get("departments", [])
    totals = result.get("totals", {})
    sum_inc = sum(float((d.get("income", 0.0) or 0.0)) for d in depts)
    sum_exp = sum(float((d.get("expense", 0.0) or 0.0)) for d in depts)
    sum_profit = sum(float((d.get("profit", 0.0) or 0.0)) for d in depts)
    if abs(sum_inc - float(totals.get("income", 0.0) or 0.0)) > 0.01:
        alerts.append("income_totals_mismatch")
    if abs(sum_exp - float(totals.get("expense", 0.0) or 0.0)) > 0.01:
        alerts.append("expense_totals_mismatch")
    if abs(sum_profit - float(totals.get("profit", 0.0) or 0.0)) > 0.01:
        alerts.append("profit_totals_mismatch")
    for d in depts:
        inc = float(d.get("income", 0.0) or 0.0)
        exp = float(d.get("expense", 0.0) or 0.0)
        pr = float(d.get("profit", 0.0) or 0.0)
        if abs(pr - (inc - exp)) > 0.01:
            alerts.append(f"profit_mismatch:{d.get('department','')}")
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
    headers = payload.get("headers", {})
    api_domain = payload.get("api_domain", "")
    query = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        inv_url = f"{api_domain}/books/v3/invoices?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        bill_url = f"{api_domain}/books/v3/bills?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.extend([inv_url, bill_url])
        _ = get_json(inv_url, headers)
        _ = get_json(bill_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "departments": [],
            "totals": {"income": 0.0, "expense": 0.0, "profit": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_dept_pnl(result)
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
