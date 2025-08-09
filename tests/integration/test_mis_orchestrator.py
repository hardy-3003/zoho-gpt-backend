from core.operate_base import OperateInput
from orchestrators.mis_orchestrator import run_mis


def test_mis_runs_with_legacy_and_logic_fallback():
    inp = OperateInput(
        org_id="test",
        start_date="2025-01-01",
        end_date="2025-01-31",
        headers={},
        api_domain="https://www.zohoapis.in",
        query="mis pnl and salary",
    )
    out = run_mis(inp, sections=["pnl", "salary", "balance"])
    assert isinstance(out.content, dict)
    sections = out.content.get("sections", {})
    # expect keys for provided sections
    assert "pnl" in sections
    assert "salary" in sections
    assert "balance" in sections  # balance should use logic fallback (L-002)
