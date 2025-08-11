import importlib

LOGIC_MODULES = [
    ("logics.logic_141_on_time_delivery_rate", "L-141"),
    ("logics.logic_142_transportation_cost_analysis", "L-142"),
    ("logics.logic_143_fleet_utilization_rate", "L-143"),
    ("logics.logic_144_fuel_consumption_tracker", "L-144"),
    ("logics.logic_145_route_optimization_alerts", "L-145"),
    ("logics.logic_146_zone_wise_carbon_score", "L-146"),
    ("logics.logic_147_green_vendor_scorecard", "L-147"),
    ("logics.logic_148_data_redundancy_detector", "L-148"),
    ("logics.logic_149_audit_flag_generator_ai_marked_high_risk_areas", "L-149"),
    ("logics.logic_150_ca_review_ready_index", "L-150"),
    ("logics.logic_151_audit_automation_wizard_step_by_step_walkthrough", "L-151"),
    ("logics.logic_152_auto_fill_for_common_journal_entries_ai_trained_on_history", "L-152"),
    ("logics.logic_153_period_lock_and_unlock_tracker", "L-153"),
    ("logics.logic_154_custom_rule_builder_for_clients_using_saas_version", "L-154"),
    ("logics.logic_155_cfo_dashboard_generator", "L-155"),
    ("logics.logic_156_financial_kpi_designer", "L-156"),
    ("logics.logic_157_self_learning_prediction_engine_for_revenue_expense", "L-157"),
    ("logics.logic_158_multi_company_consolidation_reports", "L-158"),
    ("logics.logic_159_alerts_via_telegram_slack_email_whatsapp", "L-159"),
    ("logics.logic_160_custom_user_access_logs_and_abuse_detection", "L-160"),
]

def _call(mod_name):
    m = importlib.import_module(mod_name)
    fn = getattr(m, "handle")
    return fn({"period": "2025-06", "sample_size": 5})

def test_wave10_contract_shape():
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
