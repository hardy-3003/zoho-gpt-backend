from logics.l4_contract_runtime import make_provenance, score_confidence, validate_output_contract, validate_accounting, log_with_deltas_and_anomalies

"""
Title: Debtor Ageing Buckets
ID: L-012
Tags: []
Required Inputs: schema://debtor_ageing_buckets.input.v1
Outputs: schema://debtor_ageing_buckets.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only.
"""
from helpers.rules_engine import validate_accounting

from typing import Dict, Any, List
from helpers.provenance import make_provenance
from helpers.history_store import log_with_deltas_and_anomalies
from helpers.learning_hooks import score_confidence as _score
from helpers.schema_registry import validate_output_contract
from typing import Any, Dict
LOGIC_ID = "L-XXX"

try:  # noqa: F401
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

    except Exception:

        def append_event(_logic_id: str, _data: Dict[str, Any]) -> None:  # type: ignore
            return None


LOGIC_META = {
    "id": "L-012",
    "title": "Debtor Ageing Buckets",
    "tags": ["receivables", "debtors", "ageing", "ar"],
}


def _validate_debtor_aging(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        aging = result.get("aging", {}) or {}
        unpaid = float(result.get("totals", {}).get("unpaid", 0) or 0)
        sum_bins = sum(
            float(aging.get(k, 0) or 0)
            for k in ["0-30", "31-60", "61-90", "91-180", "180+"]
        )
        if abs(unpaid - sum_bins) > 0.01:
            alerts.append("totals mismatch: unpaid != sum(buckets)")
        if unpaid > 0:
            if (
                float(aging.get("91-180", 0) or 0) + float(aging.get("180+", 0) or 0)
            ) / unpaid > 0.25:
                alerts.append("90+ share >25%")
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


def handle_impl(payload: Dict[str, Any]) -> Dict[str, Any]:
    org_id = payload.get("org_id")
    end_date = payload.get("end_date")
    headers: Dict[str, Any] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        sources.append("/books/v3/invoices?status=unpaid&date_end=")
        result = {
            "as_of": end_date,
            "aging": {
                "0-30": 0.0,
                "31-60": 0.0,
                "61-90": 0.0,
                "91-180": 0.0,
                "180+": 0.0,
            },
            "totals": {"unpaid": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
            "error": str(e),
        }

    alerts = _validate_debtor_aging(result)
    learn = _learn_from_history(payload, result)

    base_conf = 0.6
    if alerts:
        base_conf -= 0.15

    out = {
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

    try:
        prov = out.get("provenance") or {}
        prov.setdefault("sources", prov.get("sources", []))
        prov.setdefault("figures", {})
        prov["figures"].update(
            make_provenance(
                totals={
                    "endpoint": "reports/receivables",
                    "filters": {"as_of": end_date},
                }
            )
        )
        out["provenance"] = prov

        pack = log_with_deltas_and_anomalies(
            "L-012", payload, out.get("result") or {}, prov
        )
        if pack.get("alerts"):
            out["alerts"] = list(out.get("alerts", [])) + pack.get("alerts", [])
        new_conf = _score(
            sample_size=1,
            anomalies=len(pack.get("anomalies", []) or []),
            validations_failed=(
                1 if any("validation" in a for a in out.get("alerts", [])) else 0
            ),
        )
        out["confidence"] = max(float(out.get("confidence", 0.0)), float(new_conf))
        validate_output_contract(out)
    except Exception:
        pass

    return out

def handle_l4(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Call legacy compute (now handle_impl). It may already return contract-shaped output.
    core_out = handle_impl(payload)

    # If core_out already looks contract-compliant, validate and return as-is.
    if isinstance(core_out, dict) and        all(k in core_out for k in ("result","provenance","confidence","alerts")):
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
        result={"endpoint": "reports/auto", "ids": [], "filters": {"period": payload.get("period")}}
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
        anomalies=len(alerts_pack.get("anomalies", [])) if isinstance(alerts_pack, dict) else 0,
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
    
        "meta": LOGIC_META,
    }
    validate_output_contract(output)
    return output

# Export wrapper as the official handler
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    return handle_l4(payload)
