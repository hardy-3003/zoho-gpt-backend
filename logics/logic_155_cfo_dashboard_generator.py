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
    "id": "L-155",
    "title": "CFO Dashboard Generator",
    "tags": ["dashboard", "cfo", "kpi"],
}


def _validate_cfo(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        k = result.get("kpis") or {}
        # Ensure plausible bounds
        if k.get("gross_margin_pct") is not None:
            g = float(k.get("gross_margin_pct"))
            if g < -100.0 or g > 100.0:
                alerts.append("gm_out_of_bounds")
        for key in ["cash", "ar", "ap", "revenue", "wc"]:
            v = k.get(key)
            if v is not None and float(v) < 0 and key != "wc":
                alerts.append("negative_value")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        k = result.get("kpis") or {}
        if k.get("cash") is not None:
            signals.append(f"cash:{'high' if float(k['cash'])>0 else 'low'}")
        if k.get("wc") is not None:
            signals.append(f"wc:{'pos' if float(k['wc'])>=0 else 'neg'}")
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
                "summary": {"size": len((result.get("highlights") or []))},
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
        # Refer to summaries from other logics via endpoints placeholders
        pnl_url = f"{api_domain}/books/v3/reports/pnl?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        ar_url = f"{api_domain}/books/v3/invoices?status=unpaid&date_end={end_date}&organization_id={org_id}"
        ap_url = f"{api_domain}/books/v3/bills?status=unpaid&date_end={end_date}&organization_id={org_id}"
        cash_url = f"{api_domain}/books/v3/bankbalances?organization_id={org_id}"
        sources.extend([pnl_url, ar_url, ap_url, cash_url])
        _ = get_json(pnl_url, headers)
        _ = get_json(ar_url, headers)
        _ = get_json(ap_url, headers)
        _ = get_json(cash_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "kpis": {
                "cash": None,
                "ar": None,
                "ap": None,
                "revenue": None,
                "gross_margin_pct": None,
                "wc": None,
            },
            "highlights": [],
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_cfo(result)
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
