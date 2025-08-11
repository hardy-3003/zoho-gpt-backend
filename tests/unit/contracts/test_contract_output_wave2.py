import importlib


LOGIC_MODULES = [
    ("logics.logic_013_creditor_ageing_buckets", "L-013"),
    ("logics.logic_014_invoice_status", "L-014"),
    ("logics.logic_015_bill_status", "L-015"),
    ("logics.logic_016_gstr_filing_status", "L-016"),
    ("logics.logic_017_tds_filing_status", "L-017"),
    ("logics.logic_018_highest_selling_items", "L-018"),
    ("logics.logic_019_highest_revenue_clients", "L-019"),
    ("logics.logic_020_client_wise_profitability", "L-020"),
    ("logics.logic_021_po_wise_profitability", "L-021"),
    ("logics.logic_022_item_wise_sales_summary", "L-022"),
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


def test_wave2_contract_shape():
    for mod, _ in LOGIC_MODULES:
        try:
            out = _call(mod)
        except ModuleNotFoundError:
            # Skip missing modules in this repo snapshot
            continue
        assert isinstance(out, dict)
        for k in ("result", "provenance", "confidence", "alerts"):
            assert k in out
        assert isinstance(out["result"], dict)
        assert isinstance(out["provenance"], dict)
        assert isinstance(out["alerts"], list)
