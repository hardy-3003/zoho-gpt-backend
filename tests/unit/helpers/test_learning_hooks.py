from helpers.learning_hooks import (
    get_strategy,
    update_strategy_registry,
    score_confidence,
    record_feedback,
)


def test_strategy_roundtrip():
    s = get_strategy("L-TEST", "k", {"weight": 1.0})
    assert "weight" in s
    s2 = update_strategy_registry("L-TEST", "k", {"weight": 1.2})
    assert s2["weight"] == 1.2
    record_feedback("L-TEST", {"ok": True})
    assert True


def test_score_confidence_bounds_new_signature():
    c = score_confidence(sample_size=50, anomalies=1, validations_failed=0)
    assert 0.0 <= c <= 1.0
