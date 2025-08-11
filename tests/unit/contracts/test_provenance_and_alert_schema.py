from helpers.provenance import make_provenance, validate_provenance
from helpers.schema_registry import validate_output_contract


def test_provenance_validator_happy_path():
    p = make_provenance(
        x={"endpoint": "reports/pnl", "ids": [], "filters": {"period": "2025-06"}}
    )
    validate_provenance(p)


def test_output_contract_enforces_alert_item_shape():
    out = {
        "result": {"n": 1},
        "provenance": make_provenance(
            n={"endpoint": "reports/x", "ids": [], "filters": {}}
        ),
        "confidence": 0.9,
        "alerts": [{"level": "info", "msg": "ok"}],
    }
    validate_output_contract(out)
