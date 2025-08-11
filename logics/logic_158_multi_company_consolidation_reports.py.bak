"""
Title: Multi Company Consolidation Reports
ID: L-158
Tags: []
Required Inputs: schema://multi_company_consolidation_reports.input.v1
Outputs: schema://multi_company_consolidation_reports.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only.
"""
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
    "id": "L-158",
    "title": "Multi-company Consolidation Reports",
    "tags": ["consolidation", "multi-entity"],
}


def _validate_mcc(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        comps = result.get("companies") or []
        sum_rev = sum(float(c.get("revenue", 0.0) or 0.0) for c in comps)
        sum_exp = sum(float(c.get("expense", 0.0) or 0.0) for c in comps)
        sum_prof = sum(float(c.get("profit", 0.0) or 0.0) for c in comps)
        totals = result.get("totals") or {}
        if abs(sum_rev - float(totals.get("revenue", 0.0) or 0.0)) > 1e-6:
            alerts.append("totals_mismatch")
        if abs(sum_exp - float(totals.get("expense", 0.0) or 0.0)) > 1e-6:
            alerts.append("totals_mismatch")
        if abs(sum_prof - float(totals.get("profit", 0.0) or 0.0)) > 1e-6:
            alerts.append("totals_mismatch")
        if result.get("fx_policy") == "none":
            currencies = {c.get("currency") for c in comps if c.get("currency")}
            if len(currencies) > 1:
                alerts.append("mixed_currency_no_fx")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        signals.append(f"entities:{len(result.get('companies') or [])}")
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
                "summary": {"size": len(result.get("companies") or [])},
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
        tb_url = f"{api_domain}/books/v3/reports/trialbalance?date_start={start_date}&date_end={end_date}&organization_id={org_id}&group_by=company"
        sources.append(tb_url)
        _ = get_json(tb_url, headers)

        companies: List[Dict[str, Any]] = []
        result = {
            "period": {"start": start_date, "end": end_date},
            "companies": companies,
            "totals": {"revenue": 0.0, "expense": 0.0, "profit": 0.0},
            "fx_policy": "none",
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_mcc(result)
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
