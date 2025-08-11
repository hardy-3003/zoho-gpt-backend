import importlib


LOGIC_MODULES = [
    ("logics.logic_023_item_wise_profitability", "L-023"),
    ("logics.logic_024_employee_cost_trends", "L-024"),
    ("logics.logic_025_purchase_returns_summary", "L-025"),
    ("logics.logic_026_sales_returns_summary", "L-026"),
    ("logics.logic_027_dead_stock_report", "L-027"),
    ("logics.logic_028_stock_movement_report", "L-028"),
    ("logics.logic_029_cash_flow_statement", "L-029"),
    ("logics.logic_030_bank_reconciliation_status", "L-030"),
]


def _call(mod_name):
    m = importlib.import_module(mod_name)
    fn = getattr(m, "handle")
    return fn(
        {
            "org_id": "t",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "sample_size": 5,
        }
    )


def test_wave3_contract_shape():
    for mod, _ in LOGIC_MODULES:
        try:
            out = _call(mod)
        except ModuleNotFoundError:
            # Skip if absent in this repo snapshot
            continue
        assert isinstance(out, dict)
        for k in ("result", "provenance", "confidence", "alerts"):
            assert k in out
        assert isinstance(out["result"], dict)
        assert isinstance(out["provenance"], dict)
        assert isinstance(out["alerts"], list)
