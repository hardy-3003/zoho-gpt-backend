import importlib

LOGIC_MODULES = [
    ("logics.logic_081_outlier_expenses_detection", "L-081"),
    ("logics.logic_082_salary_vs_market_benchmark", "L-082"),
    ("logics.logic_083_tax_liability_estimator", "L-083"),
    ("logics.logic_084_input_tax_credit_reconciliation", "L-084"),
    ("logics.logic_085_late_filing_penalty_tracker", "L-085"),
    ("logics.logic_086_missed_payment_tracker", "L-086"),
    ("logics.logic_087_recurring_expenses_monitor", "L-087"),
    ("logics.logic_088_profit_leakage_detector", "L-088"),
    ("logics.logic_089_unbilled_revenue_tracker", "L-089"),
    ("logics.logic_090_advance_received_adjustment", "L-090"),
    ("logics.logic_091_advance_paid_adjustment", "L-091"),
    ("logics.logic_092_suspense_account_monitor", "L-092"),
    ("logics.logic_093_accounting_hygiene_score", "L-093"),
    ("logics.logic_094_business_health_score", "L-094"),
    ("logics.logic_095_scenario_simulation_engine", "L-095"),
    ("logics.logic_096_expense_optimization_engine", "L-096"),
    ("logics.logic_097_credit_rating_estimator", "L-097"),
    ("logics.logic_098_business_valuation_estimator", "L-098"),
    ("logics.logic_099_dividend_recommendation_engine", "L-099"),
    ("logics.logic_100_risk_assessment_matrix", "L-100"),
]


def _call(mod_name):
    m = importlib.import_module(mod_name)
    fn = getattr(m, "handle")
    return fn({"period": "2025-06", "sample_size": 5})


def test_wave7_contract_shape():
    # allow missing modules; enforce shape where present
    for mod, _ in LOGIC_MODULES:
        try:
            out = _call(mod)
        except ModuleNotFoundError:
            continue
        assert isinstance(out, dict)
        for k in ("result", "provenance", "confidence", "alerts"):
            assert k in out
        assert isinstance(out["result"], dict)
        assert isinstance(out["provenance"], dict)
        assert isinstance(out["alerts"], list)
