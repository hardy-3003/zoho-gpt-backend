from __future__ import annotations

from typing import Any, Dict, List

from core.operate_base import OperateInput, OperateOutput
from core.registry import route


def run_generic(input: OperateInput, logic_keywords: List[str]) -> OperateOutput:
    records: Dict[str, Any] = {}
    missing: List[str] = []
    for kw in logic_keywords:
        op = route(kw)
        if op is None:
            missing.append(kw)
            continue
        try:
            out = op(input)
            records[kw] = out.content
        except Exception as e:
            records[kw] = {"error": str(e)}

    meta = {
        "operator": "generic_orchestrator",
        "keywords": logic_keywords,
        "missing": missing,
    }
    return OperateOutput(content={"sections": records}, meta=meta)
