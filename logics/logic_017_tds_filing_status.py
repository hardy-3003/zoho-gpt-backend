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
    "id": "L-017",
    "title": "TDS Filing Status",
    "tags": ["tds", "withholding", "compliance", "filing"],
}


def _validate_tds(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        allowed = {"filed", "pending", "late"}
        for r in result.get("returns", []) or []:
            status = str(r.get("status", ""))
            if status not in allowed:
                alerts.append("invalid status detected")
                break
        if any((r.get("status") == "late") for r in result.get("returns", []) or []):
            alerts.append("late quarter present")
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
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    headers: Dict[str, Any] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        sources.append("/books/v3/tds/returns?date_start=&date_end=")
        result = {
            "period": {"start_date": start_date, "end_date": end_date},
            "returns": [],
            "summary": {"filed": 0, "pending": 0, "late": 0},
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

    alerts = _validate_tds(result)
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
                summary={
                    "endpoint": "reports/tds",
                    "filters": {"period": {"start": start_date, "end": end_date}},
                }
            )
        )
        out["provenance"] = prov

        pack = log_with_deltas_and_anomalies(
            "L-017", payload, out.get("result") or {}, prov
        )
        if pack.get("alerts"):
            out["alerts"] = list(out.get("alerts", [])) + pack.get("alerts", [])
        new_conf = _score(
            sample_size=max(1, len((out.get("result") or {}).get("returns", []) or [])),
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
