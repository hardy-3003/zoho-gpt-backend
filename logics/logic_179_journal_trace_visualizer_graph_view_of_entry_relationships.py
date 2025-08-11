"""
Title: Journal Trace Visualizer Graph View Of Entry Relationships
ID: L-179
Tags: []
Required Inputs: schema://journal_trace_visualizer_graph_view_of_entry_relationships.input.v1
Outputs: schema://journal_trace_visualizer_graph_view_of_entry_relationships.output.v1
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
    "id": "L-179",
    "title": "Journal Trace Visualizer (Graph View)",
    "tags": ["graph", "trace", "je"],
}


def _validate_jtv(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    nodes = result.get("nodes") or []
    edges = result.get("edges") or []
    node_ids = [n.get("id") for n in nodes]
    if len(set(node_ids)) != len(node_ids):
        alerts.append("duplicate_node_ids")
    valid_types = {"je", "account", "doc"}
    for n in nodes:
        if n.get("type") not in valid_types:
            alerts.append("invalid_node_type")
    node_set = set(node_ids)
    for e in edges:
        if e.get("from") not in node_set or e.get("to") not in node_set:
            alerts.append("edge_ref_missing")
    totals = result.get("totals") or {}
    if int(totals.get("nodes", 0)) != len(nodes) or int(totals.get("edges", 0)) != len(
        edges
    ):
        alerts.append("totals_mismatch")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        signals.append(
            f"graph_size:{int((result.get('totals') or {}).get('nodes', 0))}"
        )
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
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        result = {
            "period": {"start": start_date, "end": end_date},
            "nodes": nodes,
            "edges": edges,
            "totals": {"nodes": len(nodes), "edges": len(edges)},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_jtv(result)
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
