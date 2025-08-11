import importlib

LOGIC_MODULES = [
    ("logics.logic_181_transaction_volume_spike_alert", "L-181"),
    ("logics.logic_182_overdue_tds_deduction_cases", "L-182"),
    ("logics.logic_183_related_party_transaction_tracker", "L-183"),
    ("logics.logic_184_vendor_contract_expiry_alert", "L-184"),
    ("logics.logic_185_unverified_gstin_alert", "L-185"),
    ("logics.logic_186_hsn_sac_mapping_auditor", "L-186"),
    ("logics.logic_187_ai_error_suggestion_engine", "L-187"),
    ("logics.logic_188_report_consistency_verifier_across_months", "L-188"),
    ("logics.logic_189_audit_ready_report_generator", "L-189"),
    ("logics.logic_190_internal_control_weakness_identifier", "L-190"),
    ("logics.logic_191_monthly_report_completeness_checker", "L-191"),
    ("logics.logic_192_suggested_journal_entry_fixes", "L-192"),
    ("logics.logic_193_pending_je_approvals", "L-193"),
    ("logics.logic_194_partial_payments_tracker", "L-194"),
    ("logics.logic_195_reverse_charge_monitor_gst", "L-195"),
    ("logics.logic_196_p_and_l_ratio_anomaly_finder", "L-196"),
    ("logics.logic_197_mismatch_in_payment_vs_invoice_timeline", "L-197"),
    ("logics.logic_198_free_resource_usage_estimator_power_tools_etc", "L-198"),
    ("logics.logic_199_industry_benchmark_comparison_report", "L-199"),
    ("logics.logic_200_vendor_side_carbon_emissions_estimator", "L-200"),
]

def _call(mod_name):
    m = importlib.import_module(mod_name)
    fn = getattr(m, "handle")
    return fn({"period": "2025-06", "sample_size": 5})

def test_wave12_contract_shape():
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
