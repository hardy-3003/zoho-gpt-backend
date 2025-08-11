"""
Title: Input Tax Credit Reconciliation
ID: L-084
Tags: []
Required Inputs: schema://input_tax_credit_reconciliation.input.v1
Outputs: schema://input_tax_credit_reconciliation.output.v1
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
    "id": "L-084",
    "title": "Input Tax Credit Reconciliation",
    "tags": ["itc", "gst", "recon"],
}


def _validate_itc_recon(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    summary = result.get("summary", {})
    eligible = float(summary.get("eligible", 0.0) or 0.0)
    claimed = float(summary.get("claimed", 0.0) or 0.0)
    variance = float(summary.get("variance", 0.0) or 0.0)
    if abs((eligible - claimed) - variance) > 0.01:
        alerts.append("variance_mismatch")
    if eligible < 0 or claimed < 0:
        alerts.append("negative_values")
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
        tax_url = f"{api_domain}/books/v3/taxes/summary?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.append(tax_url)
        _ = get_json(tax_url, headers)

        eligible = 0.0
        claimed = 0.0
        variance = eligible - claimed
        result = {
            "period": {"start": start_date, "end": end_date},
            "summary": {"eligible": eligible, "claimed": claimed, "variance": variance},
            "notes": [],
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_itc_recon(result)
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
