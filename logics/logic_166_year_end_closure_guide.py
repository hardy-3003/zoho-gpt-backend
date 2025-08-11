from logics.l4_contract_runtime import make_provenance, score_confidence, validate_output_contract, validate_accounting, log_with_deltas_and_anomalies

"""
Title: Year End Closure Guide
ID: L-166
Tags: []
Required Inputs: schema://year_end_closure_guide.input.v1
Outputs: schema://year_end_closure_guide.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only.
"""
from helpers.learning_hooks import score_confidence
from helpers.history_store import log_with_deltas_and_anomalies
from helpers.rules_engine import validate_accounting
from helpers.provenance import make_provenance
from helpers.schema_registry import validate_output_contract

from typing import Dict, Any, List, Optional
from typing import Any, Dict
LOGIC_ID = "L-XXX"

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
    "id": "L-166",
    "title": "Year-end Closure Guide",
    "tags": ["year-end", "checklist", "close"],
}


def _validate_yecg(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    steps = result.get("steps") or []
    # step monotonic starting at 1
    last = 0
    valid_status = {"todo", "doing", "done"}
    done = 0
    for s in steps:
        step_no = int(s.get("step", 0))
        if step_no <= last:
            alerts.append("steps_not_monotonic")
        last = step_no
        st = s.get("status")
        if st not in valid_status:
            alerts.append("invalid_status")
        if st == "done":
            done += 1
    total = len(steps) if steps else 0
    progress_pct = float(result.get("progress_pct", 0.0) or 0.0)
    expected = (done / total) * 100.0 if total > 0 else 0.0
    # strict equality (deterministic construction below ensures exact match)
    if round(progress_pct, 2) != round(expected, 2):
        alerts.append("progress_mismatch")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        total = len(result.get("steps") or [])
        done = sum(1 for s in (result.get("steps") or []) if s.get("status") == "done")
        progress = int(round((done / total) * 100)) if total > 0 else 0
        signals.append(f"progress:{progress}")
        blocks = len(result.get("blocking") or [])
        signals.append(f"blocks:{blocks}")
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


def handle_impl(payload: Dict[str, Any]) -> Dict[str, Any]:
    org_id: Optional[str] = payload.get("org_id")
    start_date: Optional[str] = payload.get("start_date")
    end_date: Optional[str] = payload.get("end_date")
    headers: Dict[str, str] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        # No external sources needed; deterministic checklist
        steps: List[Dict[str, Any]] = [
            {
                "step": 1,
                "task": "Freeze periods and lock backdating",
                "owner": None,
                "status": "todo",
                "updated_at": None,
            },
            {
                "step": 2,
                "task": "Reconcile bank and cash ledgers",
                "owner": None,
                "status": "todo",
                "updated_at": None,
            },
            {
                "step": 3,
                "task": "AR/AP ageing finalization",
                "owner": None,
                "status": "todo",
                "updated_at": None,
            },
            {
                "step": 4,
                "task": "Inventory valuation cutoff",
                "owner": None,
                "status": "todo",
                "updated_at": None,
            },
            {
                "step": 5,
                "task": "Provisions and accruals",
                "owner": None,
                "status": "todo",
                "updated_at": None,
            },
            {
                "step": 6,
                "task": "Compliance filings review (GST/TDS/ROC)",
                "owner": None,
                "status": "todo",
                "updated_at": None,
            },
        ]
        done = sum(1 for s in steps if s["status"] == "done")
        total = len(steps)
        progress_pct = (done / total) * 100.0 if total > 0 else 0.0
        result = {
            "as_of": end_date,
            "steps": steps,
            "progress_pct": round(progress_pct, 2),
            "blocking": [],
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_yecg(result)
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
