from orchestrators.mis_orchestrator import run_dag, NodeSpec


def test_dag_topology_and_degradation(monkeypatch):
    # Simple 2-node chain; ensure both keys present and contract shape maintained
    nodes = [
        NodeSpec(id="L-014", import_path="logics.logic_014_invoice_status", retries=0),
        NodeSpec(
            id="L-020",
            import_path="logics.logic_020_client_wise_profitability",
            retries=0,
        ),
    ]
    edges = [("L-014", "L-020")]
    out = run_dag(nodes, edges, {"period": "2025-06"}, progress_cb=None)

    # Verify the new DAG response format
    assert "nodes" in out
    assert "edges" in out
    assert "execution_order" in out
    assert "results" in out

    # Verify both nodes are in results
    assert "L-014" in out["results"]
    assert "L-020" in out["results"]

    # Verify contract shape for each result
    for v in out["results"].values():
        assert isinstance(v, dict)
        for k in ("result", "provenance", "confidence", "alerts"):
            assert k in v
