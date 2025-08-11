"""
Title: Green Vendor Scorecard
ID: L-147
Tags: []
Required Inputs: schema://green_vendor_scorecard.input.v1
Outputs: schema://green_vendor_scorecard.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only.
"""
from typing import Dict, Any, List, Optional

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
    "id": "L-147",
    "title": "Green Vendor Scorecard",
    "tags": ["esg", "vendor", "scorecard", "scope3"],
}


def _validate_gvs(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    vendors = result.get("vendors") or []
    totals = result.get("totals") or {}
    try:
        sum_spend = 0.0
        sum_co2 = 0.0
        scores: List[float] = []
        for v in vendors:
            spend = float(v.get("spend", 0.0) or 0.0)
            co2 = float(v.get("co2e_tonnes", 0.0) or 0.0)
            score = float(v.get("score", 0.0) or 0.0)
            if spend < 0 or co2 < 0:
                alerts.append("negatives_present")
            if score < 0 or score > 100:
                alerts.append("score_out_of_bounds")
            sum_spend += spend
            sum_co2 += co2
            scores.append(score)
        t_spend = float(totals.get("spend", 0.0) or 0.0)
        t_co2 = float(totals.get("co2e_tonnes", 0.0) or 0.0)
        t_avg = float(totals.get("avg_score", 0.0) or 0.0)
        if abs(sum_spend - t_spend) > 1e-6 or abs(sum_co2 - t_co2) > 1e-6:
            alerts.append("totals_mismatch")
        if vendors:
            avg_calc = sum(scores) / len(scores)
            if abs(avg_calc - t_avg) > 1e-6:
                alerts.append("avg_score_mismatch")
        # low-score vendor >30% spend
        if sum_spend > 0:
            low_spend = 0.0
            for v in vendors:
                if float(v.get("score", 0.0) or 0.0) < 40.0:
                    low_spend += float(v.get("spend", 0.0) or 0.0)
            if (low_spend / sum_spend) * 100.0 > 30.0:
                alerts.append("low_score_spend_gt30")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    vendors = result.get("vendors") or []
    try:
        if vendors:
            top = max(vendors, key=lambda v: float(v.get("spend", 0.0) or 0.0))
            if top and top.get("vendor"):
                signals.append(f"top_vendor:{top.get('vendor')}")
        if any(a == "low_score_spend_gt30" for a in alerts):
            signals.append("low_score_spend:>30")
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
                "summary": {"size": len(vendors)},
            },
        )
    except Exception:
        pass
    return {"notes": signals[:3]}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    org_id: Optional[str] = payload.get("org_id")
    start_date: Optional[str] = payload.get("start_date")
    end_date: Optional[str] = payload.get("end_date")
    headers: Dict[str, str] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        bills_url = f"{api_domain}/books/v3/bills?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        vendors_url = f"{api_domain}/books/v3/vendors?organization_id={org_id}"
        sources.extend([bills_url, vendors_url])

        _ = get_json(bills_url, headers)
        _ = get_json(vendors_url, headers)

        vendors: List[Dict[str, Any]] = []
        result = {
            "as_of": end_date,
            "vendors": vendors,
            "totals": {"count": 0, "spend": 0.0, "co2e_tonnes": 0.0, "avg_score": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_gvs(result)
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
