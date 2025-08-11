from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.operate_base import OperateInput, OperateOutput
from core.registry import route

from helpers.pdf_extractor import extract_fields
from helpers.schema_registry import save_learned_format, validate_output_contract
from helpers.provenance import make_provenance
from helpers.history_store import log_with_deltas_and_anomalies
from helpers.learning_hooks import score_confidence
from helpers.reconciliation import reconcile_totals


def run_generic(input: OperateInput, logic_keywords: List[str]) -> OperateOutput:
    records: Dict[str, Any] = {}
    missing: List[str] = []
    for kw in logic_keywords:
        op = route(kw)
        if op is None:
            missing.append(kw)
            continue
        try:
            out = op(input)
            records[kw] = out.content
        except Exception as e:
            records[kw] = {"error": str(e)}

    meta = {
        "operator": "generic_orchestrator",
        "keywords": logic_keywords,
        "missing": missing,
    }
    return OperateOutput(content={"sections": records}, meta=meta)


# Simple nomenclature map; expand later with schema_registry rules
NOMEN_MAP: Dict[str, Dict[str, Any]] = {
    "Revenue": {"endpoint": "reports/pnl", "filters": {"section": "income"}},
    "Expenses": {"endpoint": "reports/pnl", "filters": {"section": "expense"}},
    "Net Profit": {"endpoint": "reports/pnl", "filters": {"section": "summary"}},
}


def learn_from_pdf(pdf_path: str, name: str = "mis_fixture_v1") -> Dict[str, Any]:
    """
    Extract fields from PDF and map them to Zoho provenance; save learned mapping for reuse (MSOW §4).
    """
    parsed = extract_fields(pdf_path)
    fields = parsed.get("fields", {})
    mapping: Dict[str, Any] = {}
    for k, _v in fields.items():
        hint = NOMEN_MAP.get(k)
        if hint:
            mapping[k] = {
                "endpoint": hint["endpoint"],
                "ids": [],
                "filters": hint.get("filters", {}),
            }
    path = f"docs/learned_formats/{name}.json"
    save_learned_format(name, mapping, path)
    return {"meta": parsed.get("meta", {}), "mapping_path": path, "mapping": mapping}


def generate_from_learned(
    payload: Dict[str, Any], mapping: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Use learned mapping to produce a contract-shaped output with provenance & confidence.
    The deterministic compute here is just a pass-through of mapped fields; later we'll fetch from Zoho.
    """
    # Deterministic stub: copy mapped keys from payload["source_fields"]
    src = payload.get("source_fields", {})
    result: Dict[str, Any] = {}
    prov_map: Dict[str, Any] = {}
    for k, hint in mapping.items():
        value = src.get(k)
        result[k] = value
        prov_map[k] = {
            "endpoint": hint.get("endpoint", ""),
            "ids": [],
            "filters": hint.get("filters", {}),
            "source": "zoho",
        }
    provenance = make_provenance(**prov_map)
    alerts_pack = log_with_deltas_and_anomalies(
        "L-RL-001", payload, result, provenance, period_key=payload.get("period")
    )
    confidence = score_confidence(
        sample_size=max(1, len(result)),
        anomalies=len(alerts_pack.get("anomalies", [])),
        validations_failed=0,
    )
    # Normalize alerts to contract shape (list[dict])
    raw_alerts = alerts_pack.get("alerts", []) or []
    norm_alerts = [
        a if isinstance(a, dict) else {"level": "info", "msg": str(a)}
        for a in raw_alerts
    ]

    # Reconciliation check and auto-enable
    ok, recon = reconcile_totals(result)
    alerts = norm_alerts
    if recon.get("checks"):
        # append structured reconciliation findings
        for c in recon["checks"]:
            if "msg" in c:
                c.setdefault("level", "warn")
        alerts.extend(recon["checks"])

    out = {
        "result": result,
        "provenance": provenance,
        "confidence": confidence,
        "alerts": alerts,
        "enabled": bool(ok),  # auto-enable only when reconciliation passes
    }
    validate_output_contract(out)
    return out
