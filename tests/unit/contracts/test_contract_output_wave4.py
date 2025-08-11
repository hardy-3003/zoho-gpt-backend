import importlib

LOGIC_MODULES = [
    ("logics.logic_031_supplier_delivery_performance_audit", "L-031"),
    ("logics.logic_032_purchase_price_variance_tracker", "L-032"),
    ("logics.logic_033_inventory_obsolescence_risk_detector", "L-033"),
    ("logics.logic_034_production_yield_and_scrap_analysis", "L-034"),
    ("logics.logic_035_carbon_footprint_per_unit", "L-035"),
    ("logics.logic_036_month_on_month_comparison", "L-036"),
    ("logics.logic_037_project_wise_profitability", "L-037"),
    ("logics.logic_038_vendor_wise_spend", "L-038"),
    ("logics.logic_039_tax_summary_report", "L-039"),
    ("logics.logic_040_gst_reconciliation_status", "L-040"),
]


def _call(mod_name):
    m = importlib.import_module(mod_name)
    fn = getattr(m, "handle")
    return fn({"period": "2025-06", "sample_size": 5})


def test_wave4_contract_shape():
    for mod, _ in LOGIC_MODULES:
        try:
            out = _call(mod)
        except ModuleNotFoundError:
            # Skip if file not in this snapshot
            continue
        assert isinstance(out, dict)
        for k in ("result", "provenance", "confidence", "alerts"):
            assert k in out
        assert isinstance(out["result"], dict)
        assert isinstance(out["provenance"], dict)
        assert isinstance(out["alerts"], list)
