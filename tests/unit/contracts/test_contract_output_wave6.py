import importlib
import os

LOGIC_MODULES = [
    ("logics.logic_061_production_efficiency_report", "L-061"),
    ("logics.logic_062_sales_team_performance", "L-062"),
    ("logics.logic_063_employee_productivity_analysis", "L-063"),
    ("logics.logic_064_client_acquisition_cost", "L-064"),
    ("logics.logic_065_lead_to_client_ratio", "L-065"),
    ("logics.logic_066_marketing_spend_efficiency", "L-066"),
    ("logics.logic_067_campaign_roi_summary", "L-067"),
    ("logics.logic_068_departmental_p_and_l", "L-068"),
    ("logics.logic_069_business_vertical_summary", "L-069"),
    ("logics.logic_070_inter_company_transactions", "L-070"),
    ("logics.logic_071_fund_transfer_logs", "L-071"),
    ("logics.logic_072_internal_audit_checklist", "L-072"),
    ("logics.logic_073_compliance_tracker", "L-073"),
    ("logics.logic_074_audit_trail_summary", "L-074"),
    ("logics.logic_075_error_detection_engine", "L-075"),
    ("logics.logic_076_anomaly_detection_report", "L-076"),
    ("logics.logic_077_vendor_duplication_check", "L-077"),
    ("logics.logic_078_client_duplication_check", "L-078"),
    ("logics.logic_079_data_entry_consistency", "L-079"),
    ("logics.logic_080_duplicate_invoice_detection", "L-080"),
]

def _call(mod_name):
    m = importlib.import_module(mod_name)
    fn = getattr(m, "handle")
    return fn({"period": "2025-06", "sample_size": 5})

def test_wave6_contract_shape():
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
