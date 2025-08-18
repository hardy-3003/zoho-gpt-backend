from fastapi.testclient import TestClient
from main import app
import json
import subprocess
import sys
import tempfile


def test_rest_cli_parity_smoke():
    client = TestClient(app)
    payload = {
        "plan": [
            {
                "logic": "logic_001_profit_and_loss_summary",
                "inputs": {"period": "2025-06"},
            }
        ]
    }
    r = client.post("/api/execute", json=payload)
    assert r.status_code == 200
    rest = r.json()
    assert "result" in rest and "sections" in rest["result"]
    with tempfile.NamedTemporaryFile("w+", suffix=".json") as fp:
        json.dump(payload, fp)
        fp.flush()
        out = subprocess.check_output(
            [sys.executable, "-m", "cli", "execute", "--plan", fp.name]
        )
        cli = json.loads(out.decode("utf-8"))
    assert set(rest["result"].keys()) <= set(cli["result"].keys())
