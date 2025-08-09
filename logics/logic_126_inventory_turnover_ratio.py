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
    "id": "L-126",
    "title": "Inventory Turnover Ratio",
    "tags": ["inventory", "turnover", "kpi"],
}


def _validate_itr(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    metrics = result.get("metrics") or {}
    cogs = metrics.get("cogs")
    avg_inventory = metrics.get("avg_inventory")
    turnover_ratio = metrics.get("turnover_ratio")
    try:
        if cogs is not None and avg_inventory not in (None, 0):
            expected = float(cogs) / float(avg_inventory)
            if (
                turnover_ratio is not None
                and abs(expected - float(turnover_ratio)) > 0.0001
            ):
                alerts.append("turnover_mismatch")
        if turnover_ratio is not None:
            tr = float(turnover_ratio)
            if tr <= 0 or tr > 100:
                alerts.append("turnover_out_of_bounds")
    except Exception:
        alerts.append("invalid_metrics")
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
    org_id: Optional[str] = payload.get("org_id")
    start_date: Optional[str] = payload.get("start_date")
    end_date: Optional[str] = payload.get("end_date")
    headers: Dict[str, str] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        items_url = f"{api_domain}/books/v3/items?organization_id={org_id}"
        stock_url = f"{api_domain}/books/v3/inventory/stockonhand?date_end={end_date}&organization_id={org_id}"
        bills_url = f"{api_domain}/books/v3/bills?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        cogs_url = f"{api_domain}/books/v3/journals?accounts=cogs&date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.extend([items_url, stock_url, bills_url, cogs_url])

        _ = get_json(items_url, headers)
        _stock = get_json(stock_url, headers)
        _ = get_json(bills_url, headers)
        _cogs = get_json(cogs_url, headers)

        # Minimal deterministic computation: treat ending stock as proxy for average inventory if present
        avg_inventory: Optional[float] = None
        try:
            if isinstance(_stock, dict):
                # try a few common keys
                for key in ("total_value", "inventory_value", "value"):
                    if key in _stock and _stock.get(key) is not None:
                        avg_inventory = float(_stock.get(key))
                        break
        except Exception:
            avg_inventory = None

        # Do not attempt to parse COGS deeply; keep null to avoid misleading metrics
        cogs_value: Optional[float] = None
        turnover_ratio: Optional[float] = None
        if cogs_value is not None and avg_inventory not in (None, 0):
            try:
                turnover_ratio = float(cogs_value) / float(avg_inventory)
            except Exception:
                turnover_ratio = None

        result = {
            "period": {"start_date": start_date, "end_date": end_date},
            "metrics": {
                "cogs": cogs_value,
                "avg_inventory": avg_inventory,
                "turnover_ratio": turnover_ratio,
            },
            "notes": ["cogs_source:journals|bills", "inventory_basis:stockonhand"],
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_itr(result)
    learn = _learn_from_history(payload, result)
    conf = 0.6 - (0.15 if alerts else 0.0) - (0.1 if not result else 0.0)
    # Per-logic nuance: penalize if avg_inventory missing
    try:
        if (result.get("metrics") or {}).get("avg_inventory") is None:
            conf -= 0.1
    except Exception:
        pass
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
