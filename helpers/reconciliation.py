from __future__ import annotations
from typing import Any, Dict, Tuple


def reconcile_totals(result: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """
    Minimal verifier: if keys look like Revenue/Expenses/Net Profit, assert NP = Rev - Exp (± tolerance).
    Returns (ok, report).
    """
    r = {
        k.lower().replace(" ", ""): v
        for k, v in result.items()
        if isinstance(v, (int, float))
    }
    ok = True
    reasons = []
    if {"revenue", "expenses", "netprofit"}.issubset(r.keys()):
        np_expected = r["revenue"] - r["expenses"]
        tol = max(1.0, abs(np_expected) * 0.002)  # 0.2% or ₹1 tolerance
        if abs(r["netprofit"] - np_expected) > tol:
            ok = False
            reasons.append(
                {
                    "level": "error",
                    "msg": "Net Profit mismatch beyond tolerance",
                    "expected": np_expected,
                    "actual": r["netprofit"],
                    "tolerance": tol,
                }
            )
    return ok, {"checks": reasons}
