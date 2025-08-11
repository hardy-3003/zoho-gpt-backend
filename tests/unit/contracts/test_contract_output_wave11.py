import importlib

LOGIC_MODULES = [
    ("logics.logic_161_file_upload_to_entry_mapper_e_g_invoice_pdf_je", "L-161"),
    ("logics.logic_162_voice_to_entry_convert_spoken_input_to_journal", "L-162"),
    ("logics.logic_163_advanced_filing_calendar_sync_gst_roc_tds", "L-163"),
    ("logics.logic_164_api_based_third_party_integration_framework", "L-164"),
    ("logics.logic_165_bank_feed_intelligence_layer", "L-165"),
    ("logics.logic_166_year_end_closure_guide", "L-166"),
    ("logics.logic_167_investment_vs_working_capital_allocator", "L-167"),
    ("logics.logic_168_performance_linked_pay_analyzer", "L-168"),
    ("logics.logic_169_cross_company_loan_tracker", "L-169"),
    ("logics.logic_170_government_scheme_utilization_tracker", "L-170"),
    ("logics.logic_171_legal_case_cost_monitor", "L-171"),
    ("logics.logic_172_automation_of_monthly_compliance_summary", "L-172"),
    ("logics.logic_173_dscr_and_icr_calculators_for_banking", "L-173"),
    ("logics.logic_174_auto_ca_remarks_based_on_reports", "L-174"),
    ("logics.logic_175_user_behavior_based_module_suggestions", "L-175"),
    ("logics.logic_176_scoring_system_for_business_maturity_level", "L-176"),
    ("logics.logic_177_ca_review_collaboration_toolkit", "L-177"),
    ("logics.logic_178_ai_powered_explanation_tool_explain_balance_sheet_in_plain_hindi", "L-178"),
    ("logics.logic_179_journal_trace_visualizer_graph_view_of_entry_relationships", "L-179"),
    ("logics.logic_180_interlinked_report_mapper", "L-180"),
]

def _call(mod_name):
    m = importlib.import_module(mod_name)
    fn = getattr(m, "handle")
    return fn({"period": "2025-06", "sample_size": 5})

def test_wave11_contract_shape():
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
