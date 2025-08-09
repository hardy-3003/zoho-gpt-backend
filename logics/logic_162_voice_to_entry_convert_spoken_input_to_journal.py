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
    "id": "L-162",
    "title": "Voice → Journal Entry",
    "tags": ["voice", "stt", "je"],
}

_STATUS = {"ok", "ambiguous"}


def _validate_vje(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        samples = result.get("samples") or []
        ok = 0
        amb = 0
        for s in samples:
            if s.get("status") not in _STATUS:
                alerts.append("bad_status")
            parsed = s.get("parsed") or {}
            amt = parsed.get("amount")
            if amt is not None and float(amt) < 0:
                alerts.append("negative_amount")
            if s.get("status") == "ok":
                ok += 1
            if s.get("status") == "ambiguous":
                amb += 1
        totals = result.get("totals") or {}
        if totals.get("ok") != ok or totals.get("ambiguous") != amb:
            alerts.append("totals_mismatch")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts_list: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        signals.append(f"stt_ok:{int((result.get('totals') or {}).get('ok', 0))}")
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
                "summary": {"size": len(result.get("samples") or [])},
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
        sources.append("/books/v3/ingest/voice")
        _ = get_json(
            f"{api_domain}/books/v3/ingest/voice?date_start={start_date}&date_end={end_date}&organization_id={org_id}",
            headers,
        )

        samples: List[Dict[str, Any]] = []
        result = {
            "period": {"start": start_date, "end": end_date},
            "samples": samples,
            "totals": {"ok": 0, "ambiguous": 0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_vje(result)
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
