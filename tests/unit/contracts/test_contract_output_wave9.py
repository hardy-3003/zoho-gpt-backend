import importlib

LOGIC_MODULES = [
    ("logics.logic_121_manual_journal_suspicion_detector", "L-121"),
    ("logics.logic_122_round_off_abuse_detector", "L-122"),
    ("logics.logic_123_loan_covenant_breach_alert", "L-123"),
    ("logics.logic_124_expense_inflation_flag_employee_wise", "L-124"),
    ("logics.logic_125_inventory_shrinkage_alert", "L-125"),
    ("logics.logic_126_inventory_turnover_ratio", "L-126"),
    ("logics.logic_127_stockout_frequency_alert", "L-127"),
    ("logics.logic_128_excess_inventory_analysis", "L-128"),
    ("logics.logic_129_demand_forecast_accuracy", "L-129"),
    ("logics.logic_130_order_fulfillment_cycle_time", "L-130"),
    ("logics.logic_131_supplier_lead_time_variability", "L-131"),
    ("logics.logic_132_production_capacity_utilization", "L-132"),
    ("logics.logic_133_production_downtime_analysis", "L-133"),
    ("logics.logic_134_scrap_rate_monitor", "L-134"),
    ("logics.logic_135_machine_efficiency_tracker", "L-135"),
    ("logics.logic_136_batch_yield_analysis", "L-136"),
    ("logics.logic_137_quality_defect_rate", "L-137"),
    ("logics.logic_138_return_rate_analysis", "L-138"),
    ("logics.logic_139_warranty_claims_monitor", "L-139"),
    ("logics.logic_140_customer_order_accuracy", "L-140"),
]

def _call(mod_name):
    m = importlib.import_module(mod_name)
    fn = getattr(m, "handle")
    return fn({"period": "2025-06", "sample_size": 5})

def test_wave9_contract_shape():
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
