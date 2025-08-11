from __future__ import annotations

from typing import Any, Dict, List, Tuple, Callable

from core.operate_base import OperateInput, OperateOutput
from core.registry import route
from core.logic_loader import LOGIC_REGISTRY, LogicMeta, load_all_logics


def _to_payload(inp: OperateInput) -> Dict[str, Any]:
    return {
        "org_id": inp.org_id,
        "start_date": inp.start_date,
        "end_date": inp.end_date,
        "headers": inp.headers,
        "api_domain": inp.api_domain,
        "query": inp.query,
    }


def _find_logic_by_token(token: str) -> List[Tuple[str, LogicMeta]]:
    token_l = (token or "").lower()
    matches: List[Tuple[str, LogicMeta]] = []
    for lid, (_handler, meta) in LOGIC_REGISTRY.items():
        if token_l in meta.tags or token_l in meta.title.lower():
            matches.append((lid, meta))
    return matches


def run_mis(input: OperateInput, sections: List[str]) -> OperateOutput:
    # Ensure logic registry is ready for fallback discovery
    if not LOGIC_REGISTRY:
        try:
            load_all_logics()
        except Exception:
            pass
    """Very small orchestrator that calls multiple operate modules by keywords.

    sections: list of keywords like ["pnl", "salary"]. For now, sequential
    and tolerant to missing modules.
    """
    records: Dict[str, Any] = {}
    missing: List[str] = []
    for sec in sections:
        op = route(sec)
        if op is not None:
            try:
                out = op(input)
                records[sec] = out.content
                continue
            except Exception as e:
                records[sec] = {"error": str(e)}
                continue

        # Fallback to logic handlers discovered by tags/title
        payload = _to_payload(input)
        candidates = _find_logic_by_token(sec)
        if not candidates:
            missing.append(sec)
            continue
        sec_results: Dict[str, Any] = {}
        for lid, (_handler, _meta) in [
            (lid, LOGIC_REGISTRY[lid]) for lid, _m in candidates
        ]:
            handler, meta = LOGIC_REGISTRY[lid]
            try:
                sec_results[lid] = handler(payload)
            except Exception as e:
                sec_results[lid] = {"error": str(e)}
        records[sec] = sec_results

    meta = {
        "operator": "mis_orchestrator",
        "sections": sections,
        "missing": missing,
    }
    return OperateOutput(content={"sections": records}, meta=meta)


# ------------------------ DAG Executor (additive) ------------------------


class NodeSpec:
    def __init__(
        self, id: str, import_path: str, retries: int = 1, backoff_s: float = 0.5
    ):
        self.id = id
        self.import_path = import_path
        self.retries = max(0, int(retries))
        self.backoff_s = float(backoff_s)


def _import_handle(path: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    mod_name = path
    m = __import__(mod_name, fromlist=["handle"])
    return getattr(m, "handle")


def run_dag(
    nodes: List[NodeSpec],
    edges: List[Tuple[str, str]],
    payload: Dict[str, Any],
    progress_cb: Callable[[Dict[str, Any]], None] | None = None,
) -> Dict[str, Any]:
    """Execute a small DAG of logic handlers with partial retries and graceful degradation.

    - Nodes call handle(payload) of logic modules identified by import_path
    - Edges enforce simple topological execution (assumes acyclic)
    - On failure after retries, the node emits a degraded, contract-shaped result
    """
    # indegree map
    indeg: Dict[str, int] = {n.id: 0 for n in nodes}
    for a, b in edges:
        indeg[b] = indeg.get(b, 0) + 1

    ready: List[str] = [n.id for n in nodes if indeg.get(n.id, 0) == 0]
    node_map: Dict[str, NodeSpec] = {n.id: n for n in nodes}
    out: Dict[str, Any] = {}

    while ready:
        nid = ready.pop(0)
        n = node_map[nid]
        if progress_cb:
            progress_cb({"stage": "start", "node": nid})
        handle = _import_handle(n.import_path)

        attempt = 0
        ok = False
        result: Dict[str, Any] | None = None
        last_err: str | None = None
        # attempt count = 1 + retries
        while attempt <= n.retries and not ok:
            try:
                result = handle(payload)
                ok = True
                break
            except Exception as e:  # pragma: no cover - hard to simulate consistently
                last_err = repr(e)
                attempt += 1
                if attempt <= n.retries:
                    time.sleep(n.backoff_s)

        if not ok:
            # graceful degradation envelope (contract-shaped)
            result = {
                "result": {},
                "provenance": {},
                "confidence": 0.0,
                "alerts": [{"level": "error", "msg": f"{nid} failed: {last_err}"}],
                "degraded": True,
                "reason": "retries_exhausted",
            }

        out[nid] = result  # type: ignore[arg-type]

        if progress_cb:
            progress_cb(
                {
                    "stage": "end",
                    "node": nid,
                    "degraded": bool(result.get("degraded", False)),
                }
            )

        # release successors
        for a, b in edges:
            if a == nid:
                indeg[b] = max(0, indeg.get(b, 0) - 1)
                if indeg[b] == 0 and b in node_map:
                    ready.append(b)

    return out
