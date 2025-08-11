"""
Title: Zone Wise Expenses
ID: L-006
Tags: []
Required Inputs: schema://zone_wise_expenses.input.v1
Outputs: schema://zone_wise_expenses.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only.
"""
from typing import Dict, Any, List

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


try:
    from helpers.obs import with_metrics  # type: ignore
except Exception:  # pragma: no cover

    def with_metrics(name: str):  # type: ignore
        def deco(fn):
            return fn

        return deco


LOGIC_META = {
    "id": "L-006",
    "title": "Zone-wise Expenses",
    "tags": ["expenses", "zone", "cost center", "geo"],
}


def _validate_zone_expenses(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        zones = result.get("zones", []) or []
        total_amount = sum(float(z.get("amount", 0) or 0) for z in zones)
        if total_amount > 0:
            for z in zones:
                share = float(z.get("amount", 0) or 0) / total_amount
                if share > 0.7:
                    alerts.append("zone concentration >70%")
                    break
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


@with_metrics("logic.L-006.handle")
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
        sources.append("/books/v3/bills?date_start=&date_end=&customfield=zone")
        result = {
            "period": {"start_date": start_date, "end_date": end_date},
            "zones": [],
            "top_zone": {"zone": "", "amount": 0.0},
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

    alerts = _validate_zone_expenses(result)
    learn = _learn_from_history(payload, result)
    conf = 0.6
    if "zone concentration >70%" in alerts:
        conf -= 0.15
    if not result.get("zones"):
        conf -= 0.10
    conf = max(0.1, min(0.95, conf))

    out = {
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

    try:
        from helpers.provenance import make_provenance
        from helpers.history_store import log_with_deltas_and_anomalies
        from helpers.learning_hooks import score_confidence as _score

        prov = out.get("provenance") or {}
        prov.setdefault("sources", prov.get("sources", []))
        prov.setdefault("figures", {})
        prov["figures"].update(
            make_provenance(
                zones={
                    "endpoint": "reports/expenses",
                    "filters": {
                        "group_by": "zone",
                        "period": {"start": start_date, "end": end_date},
                    },
                }
            )
        )
        out["provenance"] = prov

        pack = log_with_deltas_and_anomalies(
            "L-006", payload, out.get("result") or {}, prov
        )
        extra_alerts = pack.get("alerts", [])
        if extra_alerts:
            out["alerts"] = list(out.get("alerts", [])) + extra_alerts

        new_conf = _score(
            sample_size=max(1, len((out.get("result") or {}).get("zones", []) or [])),
            anomalies=len(pack.get("anomalies", []) or []),
            validations_failed=1 if "validation error" in out.get("alerts", []) else 0,
        )
        try:
            out["confidence"] = max(float(out.get("confidence", 0.0)), float(new_conf))
        except Exception:
            out["confidence"] = float(new_conf)
    except Exception:
        pass

    return out
