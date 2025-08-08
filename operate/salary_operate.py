from __future__ import annotations

from typing import Any, Dict

from core.operate_base import OperateInput, OperateOutput
from core.registry import register


@register("salary")
def run(input: OperateInput) -> OperateOutput:
    # Placeholder salary summary logic
    summary: Dict[str, Any] = {
        "org_id": input.org_id,
        "period": {"start": input.start_date, "end": input.end_date},
        "total_salary": 0.0,
        "employees": 0,
        "note": "Placeholder salary summary. Implement Zoho fetch + compute.",
    }
    meta = {
        "operator": "salary",
        "api_domain": input.api_domain,
        "strategy": "v0-placeholder",
    }
    return OperateOutput(content=summary, meta=meta)
