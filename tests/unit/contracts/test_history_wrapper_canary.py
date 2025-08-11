from helpers.history_store import log_with_deltas_and_anomalies


def test_history_wrapper_returns_expected_keys():
    out = log_with_deltas_and_anomalies(
        logic_id="L-CANARY",
        inputs={"period": "2025-06"},
        outputs={"k": 1},
        provenance={"k": {"endpoint": "x", "ids": [], "filters": {}}},
        period_key="2025-06",
    )
    assert isinstance(out, dict)
    for k in ("alerts", "deltas", "anomalies"):
        assert k in out
