import time
from fastapi.testclient import TestClient
from main import app


def test_execute_under_budget():
    client = TestClient(app)
    t0 = time.time()
    r = client.post(
        "/api/execute", json={"plan": [{"logic": "logic_001_profit_and_loss_summary"}]}
    )
    assert r.status_code == 200
    assert (time.time() - t0) < 1.0
