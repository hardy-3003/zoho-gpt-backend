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
    "id": "L-176",
    "title": "Scoring System for Business Maturity Level",
    "tags": ["maturity", "score", "readiness"],
}


def _validate_bml(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    pillars = result.get("pillars") or []
    total = 0.0
    for p in pillars:
        sc = float(p.get("score", 0.0) or 0.0)
        if not (0.0 <= sc <= 100.0):
            alerts.append("pillar_score_out_of_bounds")
        total += sc
    avg = (total / len(pillars)) if pillars else 0.0
    score = float(result.get("score", 0.0) or 0.0)
    if round(avg, 2) != round(score, 2):
        alerts.append("score_avg_mismatch")
    level = result.get("level")
    expected = "low"
    if score >= 80:
        expected = "high"
    elif score >= 60:
        expected = "mid"
    if level != expected:
        alerts.append("level_mapping_mismatch")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        signals.append(f"level:{result.get('level','low')}")
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
        pillars: List[Dict[str, Any]] = [
            {"pillar": "finance", "score": 0.0},
            {"pillar": "ops", "score": 0.0},
            {"pillar": "compliance", "score": 0.0},
            {"pillar": "esg", "score": 0.0},
        ]
        score = (
            round(sum(p["score"] for p in pillars) / len(pillars), 2)
            if pillars
            else 0.0
        )
        level = "low"
        if score >= 80:
            level = "high"
        elif score >= 60:
            level = "mid"
        result = {"as_of": end_date, "pillars": pillars, "score": score, "level": level}
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_bml(result)
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
