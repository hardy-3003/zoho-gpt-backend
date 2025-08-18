import json
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from main import app  # noqa: E402
from obs import log as obs_log  # noqa: E402


client = TestClient(app)


def test_rest_increments_requests_and_not_errors():
    # Call /api/execute
    payload = {
        "logic_id": "logic_001_profit_loss",
        "org_id": "60020606976",
        "period": "2025-01",
        "context": {"trace_id": "t-123"},
    }
    r = client.post("/api/execute", json=payload)
    assert r.status_code == 200

    # Read metrics
    m = client.get("/metrics.json").json()
    assert "requests_total" in m
    # labels are serialized as "surface=rest"
    assert m["requests_total"].get("surface=rest", 0) >= 1
    assert m.get("errors_total", {}).get("surface=rest", 0) == 0


def test_sse_increments_requests():
    r = client.get("/sse")
    assert r.status_code == 200
    m = client.get("/metrics.json").json()
    assert m["requests_total"].get("surface=sse", 0) >= 1


def test_cli_increments_requests(monkeypatch, tmp_path):
    # Run CLI as subprocess: python -m cli --logic-id ...
    import subprocess, sys as _sys

    cmd = [
        _sys.executable,
        "-m",
        "cli",
        "execute",
        "--logic-id",
        "logic_001_profit_loss",
        "--org-id",
        "60020606976",
        "--period",
        "2025-01",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    # The CLI writes increments to shared counters file; server should see them.
    m = client.get("/metrics.json").json()
    assert m.get("requests_total", {}).get("surface=cli", 0) >= 1


def test_structured_log_capture_trace_id(monkeypatch):
    captured = []

    def sink(payload):
        captured.append(payload)

    obs_log.set_sink(sink)

    # Make a REST call with trace_id
    payload = {
        "logic_id": "logic_001_profit_loss",
        "org_id": "60020606976",
        "period": "2025-01",
        "context": {"trace_id": "trace-abc"},
    }
    r = client.post("/api/execute", json=payload)
    assert r.status_code == 200

    # Find an execute_ok event
    evt = next((e for e in captured if e.get("evt") == "execute_ok"), None)
    assert evt is not None
    # Check trace_id presence
    assert evt.get("trace_id") == "trace-abc"
    # Validate ts format: ISO8601-like; e.g., 2025-01-01T00:00:00.000000Z
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z$", evt.get("ts", ""))
