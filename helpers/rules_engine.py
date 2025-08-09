from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


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


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def load_regulation_rules(
    rule_name: str, effective_date: Optional[str]
) -> Dict[str, Any]:
    """Load date-versioned regulation rules from config/regulations/<rule_name>.json.

    expected shape:
    {
      "versions": [
        {"effective_from": "2024-01-01", "data": {...}},
        {"effective_from": "2025-04-01", "data": {...}}
      ]
    }
    """
    config_path = os.path.join(
        os.getcwd(), "config", "regulations", f"{rule_name}.json"
    )
    if not os.path.exists(config_path):
        return {"version": None, "data": {}}
    try:
        blob = _read_json(config_path)
        versions = blob.get("versions", [])
        if not versions:
            return {"version": None, "data": {}}
        if not effective_date:
            # pick latest
            latest = max(versions, key=lambda v: v.get("effective_from", ""))
            return {
                "version": latest.get("effective_from"),
                "data": latest.get("data", {}),
            }
        dt = datetime.strptime(effective_date, "%Y-%m-%d")
        applicable = None
        for v in versions:
            try:
                vdt = datetime.strptime(
                    v.get("effective_from", "1970-01-01"), "%Y-%m-%d"
                )
                if vdt <= dt:
                    if not applicable or vdt > datetime.strptime(
                        applicable.get("effective_from"), "%Y-%m-%d"
                    ):
                        applicable = v
            except Exception:
                continue
        if not applicable:
            applicable = min(versions, key=lambda v: v.get("effective_from", ""))
        return {
            "version": applicable.get("effective_from"),
            "data": applicable.get("data", {}),
        }
    except Exception:
        return {"version": None, "data": {}}
