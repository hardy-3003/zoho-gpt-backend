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
    assert "L-014" in out and "L-020" in out
    for v in out.values():
        assert isinstance(v, dict)
        for k in ("result", "provenance", "confidence", "alerts"):
            assert k in v
