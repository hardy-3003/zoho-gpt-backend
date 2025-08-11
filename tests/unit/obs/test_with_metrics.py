import os, glob, json


def test_with_metrics_does_not_change_output():
    """Test that the decorator doesn't change function outputs"""
    from helpers.obs import with_metrics

    # Test the decorator directly
    @with_metrics("test.metrics")
    def test_function():
        return {"result": "success", "provenance": {}, "alerts": []}

    # Call the function
    out = test_function()
    assert (
        isinstance(out, dict)
        and "result" in out
        and "provenance" in out
        and "alerts" in out
    )
    assert out["result"] == "success"
    assert out["provenance"] == {}
    assert out["alerts"] == []
