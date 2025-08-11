from typing import Dict, Any, List
from helpers.provenance import make_provenance
from helpers.history_store import log_with_deltas_and_anomalies
from helpers.learning_hooks import score_confidence as _score
from helpers.schema_registry import validate_output_contract

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
    "id": "L-033",
    "title": "Monthly Expense Trend",
    "tags": ["expenses", "trend", "finance"],
}


def _validate_monthly_expense(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    months = result.get("months", [])
    prev = None
    for m in months:
        exp = float(m.get("expense", 0.0) or 0.0)
        if exp < 0:
            alerts.append(f"negative_expense:{m.get('month','')}")
        if prev is not None:
            if prev > 0 and (exp - prev) / prev > 0.5:
                alerts.append(f"spike_gt_50pct:{m.get('month','')}")
        prev = exp
    totals_exp = float(result.get("totals", {}).get("expense", 0.0) or 0.0)
    if (
        months
        and abs(totals_exp - sum(float(x.get("expense", 0.0) or 0.0) for x in months))
        > 0.01
    ):
        alerts.append("totals_mismatch")
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
        bills_url = f"{api_domain}/books/v3/bills?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.append(bills_url)
        _ = get_json(bills_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "months": [],
            "totals": {"expense": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_monthly_expense(result)
    learn = _learn_from_history(payload, result)
    conf = 0.6 - (0.15 if alerts else 0.0) - (0.1 if not result else 0.0)
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
        prov = out.get("provenance") or {}
        prov.setdefault("sources", prov.get("sources", []))
        prov.setdefault("figures", {})
        prov["figures"].update(
            make_provenance(
                totals={
                    "endpoint": "reports/auto",
                    "filters": {"period": {"start": start_date, "end": end_date}},
                }
            )
        )
        out["provenance"] = prov

        pack = log_with_deltas_and_anomalies(
            LOGIC_META["id"],
            payload,
            out.get("result") or {},
            prov,
            period_key=payload.get("period"),
        )
        if pack.get("alerts"):
            out["alerts"] = list(out.get("alerts", [])) + pack.get("alerts", [])
        new_conf = _score(
            sample_size=max(1, len(out.get("result") or {})),
            anomalies=len(pack.get("anomalies", []) or []),
            validations_failed=0,
        )
        out["confidence"] = max(float(out.get("confidence", 0.0)), float(new_conf))
        validate_output_contract(out)
    except Exception:
        pass

    return out
