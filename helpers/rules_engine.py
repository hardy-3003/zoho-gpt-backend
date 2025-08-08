from __future__ import annotations

from typing import Any, Dict, List


def validate_accounting(result: Dict[str, Any]) -> List[str]:
    # Minimal placeholder rules
    alerts: List[str] = []
    if result.get("net_profit") is not None:
        try:
            rev = float(result.get("revenue", 0) or 0)
            cogs = float(result.get("cogs", 0) or 0)
            exp = float(result.get("expenses", 0) or 0)
            calc_np = rev - cogs - exp
            np = float(result.get("net_profit", 0) or 0)
            if abs(calc_np - np) > 1e-6:
                alerts.append(
                    "Net profit does not reconcile with revenue - cogs - expenses"
                )
        except Exception:
            alerts.append("Failed to validate P&L arithmetic")
    return alerts
