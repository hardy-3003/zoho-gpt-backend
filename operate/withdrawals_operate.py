from __future__ import annotations

from typing import Any, Dict

from core.operate_base import OperateInput, OperateOutput
from core.registry import register


@register("withdrawal")
@register("withdrawals")
def run(input: OperateInput) -> OperateOutput:
    # Placeholder partner withdrawals summary
    data: Dict[str, Any] = {
        "org_id": input.org_id,
        "period": {"start": input.start_date, "end": input.end_date},
        "total_withdrawals": 0.0,
        "transactions": [],
        "note": "Placeholder withdrawals. Implement Zoho fetch + compute.",
    }
    meta = {
        "operator": "withdrawals",
        "api_domain": input.api_domain,
        "strategy": "v0-placeholder",
    }
    return OperateOutput(content=data, meta=meta)
