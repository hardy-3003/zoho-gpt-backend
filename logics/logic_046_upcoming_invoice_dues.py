"""
Title: Upcoming Invoice Dues
ID: L-046
Tags: []
Required Inputs: schema://upcoming_invoice_dues.input.v1
Outputs: schema://upcoming_invoice_dues.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only."""
from typing import Dict, Any, List
from helpers.learning_hooks import score_confidence
from helpers.history_store import log_with_deltas_and_anomalies
from helpers.rules_engine import validate_accounting
from helpers.provenance import make_provenance
from helpers.schema_registry import validate_output_contract

LOGIC_ID = "L-046"


from datetime import datetime

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
    "id": "L-046",
    "title": "Upcoming Invoice Dues",
    "tags": ["ar", "due", "alerts"],
}


def _validate_upcoming_invoices(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    invoices = result.get("invoices", [])
    totals = result.get("totals", {})
    if int(totals.get("count", 0) or 0) != len(invoices):
        alerts.append("count_mismatch")
    sum_amount = sum(float((x.get("amount", 0.0) or 0.0)) for x in invoices)
    if abs(sum_amount - float(totals.get("amount", 0.0) or 0.0)) > 0.01:
        alerts.append("amount_total_mismatch")
    for inv in invoices:
        if int(inv.get("days_to_due", 0) or 0) < -365:
            alerts.append(f"days_to_due_out_of_bounds:{inv.get('invoice','')}")
        if int(inv.get("days_to_due", 0) or 0) < 0:
            alerts.append(f"overdue:{inv.get('invoice','')}")
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
    
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    # === Keep existing deterministic compute as-is (AEP §6 No Rewrites) ===
    # If this module uses a different function name (e.g., run/execute/build_report), use that name here.
    result = compute(payload)  # replace name if different in this file

    # Validations (non-fatal)
    validations_failed = 0
    try:
        validate_accounting(result)
    except Exception:
        validations_failed += 1

    # Minimal provenance (expand per-figure later per MSOW §2)
    prov = make_provenance(
        result={"endpoint":"reports/auto","ids":[],"filters":{"period": payload.get("period")}}
    )

    # History + Deltas + Anomalies (MSOW §5)
    alerts_pack = log_with_deltas_and_anomalies(
        LOGIC_ID, payload, result, prov, period_key=payload.get("period")
    )

    # Confidence (learnable; AEP §1)
    confidence = score_confidence(
        sample_size=max(1, len(result) if hasattr(result, "__len__") else 1),
        anomalies=len(alerts_pack.get("anomalies", [])),
        validations_failed=validations_failed,
    )

    output = {
        "result": result,
        "provenance": prov,
        "confidence": confidence,
        "alerts": alerts_pack.get("alerts", []),
    }
    validate_output_contract(output)
    return output

def _days_between(d1: str, d2: str) -> int:
    try:
        d1_dt = datetime.strptime(d1, "%Y-%m-%d")
        d2_dt = datetime.strptime(d2, "%Y-%m-%d")
        return (d2_dt - d1_dt).days
    except Exception:
        return 0


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
        inv_url = f"{api_domain}/books/v3/invoices?status=unpaid&due_start={start_date}&due_end={end_date}&organization_id={org_id}"
        sources.append(inv_url)
        _ = get_json(inv_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "invoices": [],
            "totals": {"count": 0, "amount": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_upcoming_invoices(result)
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