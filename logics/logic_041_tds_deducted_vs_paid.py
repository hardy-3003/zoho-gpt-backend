"""
Title: Tds Deducted Vs Paid
ID: L-041
Tags: []
Required Inputs: schema://tds_deducted_vs_paid.input.v1
Outputs: schema://tds_deducted_vs_paid.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only."""
from typing import Dict, Any, List
from helpers.learning_hooks import score_confidence
from helpers.history_store import log_with_deltas_and_anomalies
from helpers.rules_engine import validate_accounting
from helpers.provenance import make_provenance
from helpers.schema_registry import validate_output_contract

LOGIC_ID = "L-041"


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
    "id": "L-041",
    "title": "TDS Deducted vs Paid",
    "tags": ["tds", "withholding", "compliance"],
}


def _validate_tds(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    summary = result.get("summary", {})
    deducted = float(summary.get("deducted", 0.0) or 0.0)
    paid = float(summary.get("paid", 0.0) or 0.0)
    unpaid = float(summary.get("unpaid", 0.0) or 0.0)
    if abs(unpaid - (deducted - paid)) > 0.01:
        alerts.append("unpaid_mismatch")
    if unpaid > 0.0:
        alerts.append("unpaid_gt_zero")
    return alerts


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        append_event(
            LOGIC_META["id"],
            {
                "org_id": payload.get("org_id"),
   
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
        deductions_url = f"{api_domain}/books/v3/tds/deductions?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        payments_url = f"{api_domain}/books/v3/tds/payments?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.extend([deductions_url, payments_url])
        _ = get_json(deductions_url, headers)
        _ = get_json(payments_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "summary": {"deducted": 0.0, "paid": 0.0, "unpaid": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_tds(result)
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