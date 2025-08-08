from fastapi.testclient import TestClient
from main import app


def test_manifest():
    client = TestClient(app)
    r = client.get("/mcp/manifest")
    assert r.status_code == 200
    data = r.json()
    assert data["name"]
    assert any(t["type"] == "search" for t in data["tools"])  # basic shape
