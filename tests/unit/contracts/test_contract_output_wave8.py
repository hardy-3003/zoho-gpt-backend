import importlib

LOGIC_MODULES = [
    ("logics.logic_101_cash_reserve_advisor", "L-101"),
    ("logics.logic_102_strategic_suggestion_engine", "L-102"),
    ("logics.logic_103_auto_reconciliation_suggestion", "L-103"),
    ("logics.logic_104_fabrication_vs_billing_variance", "L-104"),
    ("logics.logic_105_boq_vs_actual_cost", "L-105"),
    ("logics.logic_106_material_rate_change_monitor", "L-106"),
    ("logics.logic_107_inter_branch_transfer_log", "L-107"),
    ("logics.logic_108_employee_reimbursement_check", "L-108"),
    ("logics.logic_109_pending_approvals_summary", "L-109"),
    ("logics.logic_110_backdated_entry_detector", "L-110"),
    ("logics.logic_111_late_vendor_payment_penalty_alert", "L-111"),
    ("logics.logic_112_margin_pressure_tracker_cost_vs_price", "L-112"),
    ("logics.logic_113_contract_breach_detection", "L-113"),
    ("logics.logic_114_client_risk_profiling", "L-114"),
    ("logics.logic_115_invoice_bounce_predictor", "L-115"),
    ("logics.logic_116_high_risk_vendor_pattern", "L-116"),
    ("logics.logic_117_multi_gstin_entity_aggregator", "L-117"),
    ("logics.logic_118_real_time_working_capital_snapshot", "L-118"),
    ("logics.logic_119_invoice_duplication_prevention_on_entry", "L-119"),
    ("logics.logic_120_cross_period_adjustment_tracker", "L-120"),
]


def _call(mod_name):
    m = importlib.import_module(mod_name)
    fn = getattr(m, "handle")
    return fn({"period": "2025-06", "sample_size": 5})


def test_wave8_contract_shape():
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
