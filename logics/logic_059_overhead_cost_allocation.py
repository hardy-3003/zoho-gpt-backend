"""
Title: Overhead Cost Allocation
ID: L-059
Tags: []
Required Inputs: schema://overhead_cost_allocation.input.v1
Outputs: schema://overhead_cost_allocation.output.v1
Assumptions:
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only."""

from typing import Dict, Any, List
from helpers.learning_hooks import score_confidence
from helpers.history_store import log_with_deltas_and_anomalies
from helpers.rules_engine import validate_accounting
from helpers.provenance import make_provenance
from helpers.schema_registry import validate_output_contract
from typing import Any, Dict

LOGIC_ID = "L-059"


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
    "id": "L-059",
    "title": "Overhead Cost Allocation",
    "tags": ["overhead", "allocation", "manufacturing"],
}


def _validate_overhead_alloc(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    allocations = result.get("allocations", [])
    drivers = result.get("drivers", [])
    total_overhead = float(result.get("totals", {}).get("overhead", 0.0) or 0.0)
    sum_alloc = sum(float((a.get("allocated", 0.0) or 0.0)) for a in allocations)
    if abs(sum_alloc - total_overhead) > 0.01:
        alerts.append("allocations_do_not_sum_to_overhead")
    if any((d.get("base") or 0.0) < 0 for d in drivers):
        alerts.append("negative_driver_base")
    return alerts


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        append_event(
            LOGIC_META["id"],
            {
                "org_id": payload.get("org_id"),
                "result": result,
            },
        )
    except Exception:
        pass
    return {"notes": []}


def handle_impl(payload: Dict[str, Any]) -> Dict[str, Any]:
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
        result={
            "endpoint": "reports/auto",
            "ids": [],
            "filters": {"period": payload.get("period")},
        }
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


def handle_impl(payload: Dict[str, Any]) -> Dict[str, Any]:
    org_id = payload.get("org_id")
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    headers = payload.get("headers", {})
    api_domain = payload.get("api_domain", "")
    query = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        journals_url = f"{api_domain}/books/v3/journals?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.append(journals_url)
        _ = get_json(journals_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "drivers": [],
            "allocations": [],
            "totals": {"overhead": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_overhead_alloc(result)
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


def handle_l4(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Call legacy compute (now handle_impl). It may already return contract-shaped output.
    core_out = handle_impl(payload)

    # If core_out already looks contract-compliant, validate and return as-is.
    if isinstance(core_out, dict) and all(
        k in core_out for k in ("result", "provenance", "confidence", "alerts")
    ):
        try:
            validate_output_contract(core_out)
        except Exception:
            # If legacy contract is off, fall back to wrapper path below.
            pass
        else:
            return core_out

    # Otherwise, treat core_out as the raw result payload.
    result = core_out if isinstance(core_out, dict) else {"value": core_out}

    # Non-fatal accounting validation
    validations_failed = 0
    try:
        validate_accounting(result)
    except Exception:
        validations_failed += 1

    # Minimal provenance (period-aware)
    prov = make_provenance(
        result={
            "endpoint": "reports/auto",
            "ids": [],
            "filters": {"period": payload.get("period")},
        }
    )

    # History + Deltas + Anomalies
    logic_id = globals().get("LOGIC_ID")
    alerts_pack = log_with_deltas_and_anomalies(
        logic_id if isinstance(logic_id, str) else "L-XXX",
        payload,
        result,
        prov,
        period_key=payload.get("period"),
    )

    # Confidence scorer (learnable)
    sample_size = 1
    try:
        sample_size = max(1, len(result))  # if dict, len = #keys
    except Exception:
        sample_size = 1

    confidence = score_confidence(
        sample_size=sample_size,
        anomalies=(
            len(alerts_pack.get("anomalies", []))
            if isinstance(alerts_pack, dict)
            else 0
        ),
        validations_failed=validations_failed,
    )

    # Convert string alerts to dict format for schema compliance
    raw_alerts = alerts_pack.get("alerts", []) if isinstance(alerts_pack, dict) else []
    alerts = []
    for alert in raw_alerts:
        if isinstance(alert, str):
            alerts.append({"msg": alert, "level": "info"})
        elif isinstance(alert, dict):
            alerts.append(alert)
        else:
            alerts.append({"msg": str(alert), "level": "info"})

    output = {
        "result": result,
        "provenance": prov,
        "confidence": confidence,
        "alerts": alerts,
    }
    validate_output_contract(output)
    return output


# Export wrapper as the official handler
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    return handle_l4(payload)
