"""
Title: Balance Sheet
ID: L-002
Tags: []
Required Inputs: schema://balance_sheet.input.v1
Outputs: schema://balance_sheet.output.v1
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


LOGIC_META = {
    "id": "L-002",
    "title": "Balance Sheet",
    "tags": ["balance", "assets", "liabilities", "equity", "position"],
}


def _validate_balance_sheet(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        totals = result.get("totals", {}) or {}
        a = float(totals.get("assets", 0) or 0)
        le = float(totals.get("liabilities_plus_equity", 0) or 0)
        if abs(a - le) > 0.01:
            alerts.append("unbalanced: assets != liabilities+equity")
        for line in result.get("assets", []) or []:
            if float(line.get("amount", 0) or 0) < 0:
                alerts.append("negative asset line")
                break
        for line in result.get("equity", []) or []:
            if float(line.get("amount", 0) or 0) < 0:
                alerts.append("negative equity line")
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
        sources.append("/books/v3/chartofaccounts")
        sources.append("/books/v3/journals?date_end=")
        result = {
            "as_of": end_date,
            "assets": [],
            "liabilities": [],
            "equity": [],
            "totals": {"assets": 0.0, "liabilities_plus_equity": 0.0},
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

    alerts = _validate_balance_sheet(result)
    learn = _learn_from_history(payload, result)
    conf = 0.6
    if any(a.startswith("unbalanced") for a in alerts):
        conf -= 0.15
    if (
        not result.get("assets")
        and not result.get("liabilities")
        and not result.get("equity")
    ):
        conf -= 0.10
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
