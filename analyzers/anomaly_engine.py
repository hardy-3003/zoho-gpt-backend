from __future__ import annotations

from typing import Any, Dict, List


def find_simple_anomalies(current: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    if current.get("expenses", 0) and current.get("revenue", 0):
        try:
            rev = float(current.get("revenue", 0) or 0)
            exp = float(current.get("expenses", 0) or 0)
            if exp > rev * 2:
                alerts.append("Expenses are more than 2x revenue (simple threshold)")
        except Exception:
            pass
    return alerts
