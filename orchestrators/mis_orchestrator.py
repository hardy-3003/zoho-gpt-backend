from __future__ import annotations

from typing import Any, Dict, List

from core.operate_base import OperateInput, OperateOutput
from core.registry import route


def run_mis(input: OperateInput, sections: List[str]) -> OperateOutput:
    """Very small orchestrator that calls multiple operate modules by keywords.

    sections: list of keywords like ["pnl", "salary"]. For now, sequential
    and tolerant to missing modules.
    """
    records: Dict[str, Any] = {}
    missing: List[str] = []
    for sec in sections:
        op = route(sec)
        if op is None:
            missing.append(sec)
            continue
        try:
            out = op(input)
            records[sec] = out.content
        except Exception as e:
            records[sec] = {"error": str(e)}

    meta = {
        "operator": "mis_orchestrator",
        "sections": sections,
        "missing": missing,
    }
    return OperateOutput(content={"sections": records}, meta=meta)
