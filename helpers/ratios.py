"""
Ratio calculation helpers for deterministic financial ratio computations.
Used by logic_231_ratio_impact_advisor for covenant monitoring.
"""

from typing import Dict, Any, List, Optional
import json
from dataclasses import dataclass


@dataclass
class RatioResult:
    """Result of ratio calculation with metadata."""

    value: float
    components: Dict[str, float]
    calculation_method: str
    confidence: float


def fetch_trial_balance(org_id: str, period: str) -> Dict[str, Any]:
    """
    Fetch trial balance for ratio calculations.

    Args:
        org_id: Organization identifier
        period: Period in YYYY-MM format

    Returns:
        Trial balance data structure
    """
    # TODO: Implement actual TB fetch from Zoho API
    # This is a placeholder implementation
    return {
        "current_assets": 1000000.0,
        "current_liabilities": 500000.0,
        "inventory": 200000.0,
        "total_debt": 800000.0,
        "shareholders_equity": 1200000.0,
        "ebitda": 300000.0,
        "interest_expense": 50000.0,
        "non_cash_expenses": 40000.0,
        "taxes": 60000.0,
        "principal_due": 100000.0,
    }


def compute_current_ratio(tb: Dict[str, Any]) -> RatioResult:
    """Compute Current Ratio = Current Assets / Current Liabilities."""
    current_assets = tb.get("current_assets", 0.0)
    current_liabilities = tb.get("current_liabilities", 0.0)

    if current_liabilities == 0:
        return RatioResult(
            value=float("inf"),
            components={
                "current_assets": current_assets,
                "current_liabilities": current_liabilities,
            },
            calculation_method="current_ratio",
            confidence=0.0,
        )

    ratio = current_assets / current_liabilities

    return RatioResult(
        value=ratio,
        components={
            "current_assets": current_assets,
            "current_liabilities": current_liabilities,
        },
        calculation_method="current_ratio",
        confidence=1.0,
    )


def compute_quick_ratio(tb: Dict[str, Any]) -> RatioResult:
    """Compute Quick Ratio = (Current Assets - Inventory) / Current Liabilities."""
    current_assets = tb.get("current_assets", 0.0)
    inventory = tb.get("inventory", 0.0)
    current_liabilities = tb.get("current_liabilities", 0.0)

    if current_liabilities == 0:
        return RatioResult(
            value=float("inf"),
            components={
                "current_assets": current_assets,
                "inventory": inventory,
                "current_liabilities": current_liabilities,
            },
            calculation_method="quick_ratio",
            confidence=0.0,
        )

    ratio = (current_assets - inventory) / current_liabilities

    return RatioResult(
        value=ratio,
        components={
            "current_assets": current_assets,
            "inventory": inventory,
            "current_liabilities": current_liabilities,
        },
        calculation_method="quick_ratio",
        confidence=1.0,
    )


def compute_debt_to_equity(tb: Dict[str, Any]) -> RatioResult:
    """Compute Debt-to-Equity = Total Debt / Shareholder's Equity."""
    total_debt = tb.get("total_debt", 0.0)
    shareholders_equity = tb.get("shareholders_equity", 0.0)

    if shareholders_equity == 0:
        return RatioResult(
            value=float("inf"),
            components={
                "total_debt": total_debt,
                "shareholders_equity": shareholders_equity,
            },
            calculation_method="debt_to_equity",
            confidence=0.0,
        )

    ratio = total_debt / shareholders_equity

    return RatioResult(
        value=ratio,
        components={
            "total_debt": total_debt,
            "shareholders_equity": shareholders_equity,
        },
        calculation_method="debt_to_equity",
        confidence=1.0,
    )


def compute_interest_coverage(tb: Dict[str, Any]) -> RatioResult:
    """Compute Interest Coverage = EBITDA / Interest Expense."""
    ebitda = tb.get("ebitda", 0.0)
    interest_expense = tb.get("interest_expense", 0.0)

    if interest_expense == 0:
        return RatioResult(
            value=float("inf"),
            components={"ebitda": ebitda, "interest_expense": interest_expense},
            calculation_method="interest_coverage",
            confidence=0.0,
        )

    ratio = ebitda / interest_expense

    return RatioResult(
        value=ratio,
        components={"ebitda": ebitda, "interest_expense": interest_expense},
        calculation_method="interest_coverage",
        confidence=1.0,
    )


def compute_dscr(tb: Dict[str, Any]) -> RatioResult:
    """Compute DSCR = (EBITDA + Non-cash expenses - Taxes) / (Interest + Principal due)."""
    ebitda = tb.get("ebitda", 0.0)
    non_cash_expenses = tb.get("non_cash_expenses", 0.0)
    taxes = tb.get("taxes", 0.0)
    interest_expense = tb.get("interest_expense", 0.0)
    principal_due = tb.get("principal_due", 0.0)

    numerator = ebitda + non_cash_expenses - taxes
    denominator = interest_expense + principal_due

    if denominator == 0:
        return RatioResult(
            value=float("inf"),
            components={
                "ebitda": ebitda,
                "non_cash_expenses": non_cash_expenses,
                "taxes": taxes,
                "interest_expense": interest_expense,
                "principal_due": principal_due,
            },
            calculation_method="dscr",
            confidence=0.0,
        )

    ratio = numerator / denominator

    return RatioResult(
        value=ratio,
        components={
            "ebitda": ebitda,
            "non_cash_expenses": non_cash_expenses,
            "taxes": taxes,
            "interest_expense": interest_expense,
            "principal_due": principal_due,
        },
        calculation_method="dscr",
        confidence=1.0,
    )


def compute_working_capital(tb: Dict[str, Any]) -> float:
    """Compute Working Capital = Current Assets - Current Liabilities."""
    current_assets = tb.get("current_assets", 0.0)
    current_liabilities = tb.get("current_liabilities", 0.0)
    return current_assets - current_liabilities


def compute_all(tb: Dict[str, Any]) -> Dict[str, float]:
    """
    Compute all ratios for a trial balance.

    Args:
        tb: Trial balance data

    Returns:
        Dictionary of ratio name to value
    """
    ratios = {}

    current_ratio = compute_current_ratio(tb)
    ratios["current_ratio"] = current_ratio.value

    quick_ratio = compute_quick_ratio(tb)
    ratios["quick_ratio"] = quick_ratio.value

    debt_to_equity = compute_debt_to_equity(tb)
    ratios["de_ratio"] = debt_to_equity.value

    interest_coverage = compute_interest_coverage(tb)
    ratios["icr"] = interest_coverage.value

    dscr = compute_dscr(tb)
    ratios["dscr"] = dscr.value

    working_capital = compute_working_capital(tb)
    ratios["working_capital"] = working_capital

    return ratios


def is_near_breach(ratios: Dict[str, float], covenants: Dict[str, Any]) -> bool:
    """
    Check if any ratio is near breach threshold (within 10% buffer).

    Args:
        ratios: Current ratio values
        covenants: Covenant configuration

    Returns:
        True if any ratio is near breach
    """
    thresholds = covenants.get("thresholds", {})
    buffer_pct = covenants.get("buffer_percentage", 0.10)  # 10% default

    for ratio_name, current_value in ratios.items():
        if ratio_name in thresholds:
            threshold = thresholds[ratio_name]
            buffer = threshold * buffer_pct

            # For ratios where lower is worse (DSCR, ICR, current_ratio, quick_ratio)
            if ratio_name in ["dscr", "icr", "current_ratio", "quick_ratio"]:
                if current_value <= (threshold + buffer):
                    return True
            # For ratios where higher is worse (de_ratio)
            elif ratio_name in ["de_ratio"]:
                if current_value >= (threshold - buffer):
                    return True

    return False


def generate_suggestions(
    je: Dict[str, Any], tb: Dict[str, Any], covenants: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Generate suggestions for improving ratios.

    Args:
        je: Proposed journal entry
        tb: Trial balance
        covenants: Covenant configuration

    Returns:
        List of suggestion objects
    """
    # TODO: Implement sophisticated suggestion generation
    # This is a placeholder implementation

    suggestions = []

    # Example suggestion for DSCR improvement
    if "dscr" in covenants.get("thresholds", {}):
        suggestions.append(
            {
                "title": "Consider deferring non-essential expenses",
                "rationale": "Improves DSCR by reducing cash outflows",
                "compliance_refs": ["Standard accounting practices"],
                "projected_after": {"dscr": covenants["thresholds"]["dscr"] + 0.1},
                "posting_patch": {
                    "reclass": [{"from": "expenses", "to": "deferred_expenses"}]
                },
            }
        )

    return suggestions
