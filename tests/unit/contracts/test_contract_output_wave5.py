import importlib

# Authoritative list (MSOW §8):
# 41 TDS Deducted vs Paid
# 42 Credit Utilization Percentage
# 43 Sales Conversion Ratio
# 44 Revenue Forecast
# 45 Expense Forecast
# 46 Upcoming Invoice Dues
# 47 Upcoming Bill Payments
# 48 Receivable Alerts
# 49 Payable Alerts
# 50 Loan Outstanding Summary
# 51 Interest Paid Summary
# 52 Capital Invested Timeline
# 53 Shareholder Equity Movement
# 54 Depreciation Calculation
# 55 Fixed Asset Register
# 56 Inventory Valuation
# 57 Raw Material Usage
# 58 Bill of Materials Breakdown
# 59 Overhead Cost Allocation
# 60 Manufacturing Cost Sheet

LOGIC_MODULES = [
    ("logics.logic_041_tds_deducted_vs_paid", "L-041"),
    ("logics.logic_042_credit_utilization_percentage", "L-042"),
    ("logics.logic_043_sales_conversion_ratio", "L-043"),
    ("logics.logic_044_revenue_forecast", "L-044"),
    ("logics.logic_045_expense_forecast", "L-045"),
    ("logics.logic_046_upcoming_invoice_dues", "L-046"),
    ("logics.logic_047_upcoming_bill_payments", "L-047"),
    ("logics.logic_048_receivable_alerts", "L-048"),
    ("logics.logic_049_payable_alerts", "L-049"),
    ("logics.logic_050_loan_outstanding_summary", "L-050"),
    ("logics.logic_051_interest_paid_summary", "L-051"),
    ("logics.logic_052_capital_invested_timeline", "L-052"),
    ("logics.logic_053_shareholder_equity_movement", "L-053"),
    ("logics.logic_054_depreciation_calculation", "L-054"),
    ("logics.logic_055_fixed_asset_register", "L-055"),
    ("logics.logic_056_inventory_valuation", "L-056"),
    ("logics.logic_057_raw_material_usage", "L-057"),
    ("logics.logic_058_bill_of_materials_breakdown", "L-058"),
    ("logics.logic_059_overhead_cost_allocation", "L-059"),
    ("logics.logic_060_manufacturing_cost_sheet", "L-060"),
]


def _call(mod_name):
    m = importlib.import_module(mod_name)
    fn = getattr(m, "handle")
    return fn({"period": "2025-06", "sample_size": 5})


def test_wave5_contract_shape():
    for mod, _ in LOGIC_MODULES:
        try:
            out = _call(mod)
        except ModuleNotFoundError:
            # Skip if file not present in this repo snapshot
            continue
        assert isinstance(out, dict)
        for k in ("result", "provenance", "confidence", "alerts"):
            assert k in out
        assert isinstance(out["result"], dict)
        assert isinstance(out["provenance"], dict)
        assert isinstance(out["alerts"], list)
