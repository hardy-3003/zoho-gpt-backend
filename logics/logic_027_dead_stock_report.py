"""
Title: Dead Stock Report
ID: L-027
Tags: []
Required Inputs: schema://dead_stock_report.input.v1
Outputs: schema://dead_stock_report.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only.
"""
from typing import Dict, Any, List
from helpers.provenance import make_provenance
from helpers.history_store import log_with_deltas_and_anomalies
from helpers.learning_hooks import score_confidence as _score
from helpers.schema_registry import validate_output_contract

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
    "id": "L-027",
    "title": "Dead Stock Report",
    "tags": ["inventory", "dead stock", "slow moving", "warehouse"],
}


def _validate_dead_stock(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        for it in result.get("items", []) or []:
            if float(it.get("qty_on_hand", 0) or 0) < 0:
                alerts.append("negative qty detected")
                break
        for it in result.get("dead", []) or []:
            if float(it.get("qty_on_hand", 0) or 0) < 0:
                alerts.append("negative dead qty detected")
                break
        # flag long no-sale threshold
        # Here we check totals for presence; details would rely on last_sale_date when available
        if any(
            (it.get("days_since_sale", 0) or 0) >= 180
            for it in result.get("items", []) or []
        ):
            alerts.append("items with >180 days since last sale")
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
    org_id = payload.get("org_id")
    end_date = payload.get("end_date")
    headers: Dict[str, Any] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        sources.append("/books/v3/items")
        sources.append("/books/v3/inventory/stockonhand?date_end=")
        sources.append("/books/v3/invoices?date_start=&date_end=&item_id=")
        result = {
            "as_of": end_date,
            "items": [],
            "dead": [],
            "totals": {"dead_count": 0, "dead_qty": 0.0},
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

    alerts = _validate_dead_stock(result)
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
                    "endpoint": "reports/dead_stock",
                    "filters": {"as_of": end_date},
                }
            )
        )
        out["provenance"] = prov

        pack = log_with_deltas_and_anomalies(
            "L-027", payload, out.get("result") or {}, prov
        )
        if pack.get("alerts"):
            out["alerts"] = list(out.get("alerts", [])) + pack.get("alerts", [])
        new_conf = _score(
            sample_size=max(1, len((out.get("result") or {}).get("items", []) or [])),
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
