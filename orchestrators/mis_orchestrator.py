from __future__ import annotations

from typing import Any, Dict, List, Tuple

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
