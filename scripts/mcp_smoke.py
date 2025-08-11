import json, sys, os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


BASE = os.environ.get("MCP_BASE", "http://127.0.0.1:8000")
TOKEN = os.environ.get("MCP_SECRET", "default-secret")
logics = [
    {"logic_id": "L-014", "payload": {"period": "2025-06", "sample_size": 5}},
    {"logic_id": "L-020", "payload": {"period": "2025-06", "sample_size": 5}},
    {"logic_id": "L-006", "payload": {"period": "2025-06", "sample_size": 5}},
]


def post(path, data):
    body = json.dumps(data).encode("utf-8")
    req = Request(
        f"{BASE}{path}",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"},
        method="POST",
    )
    return json.loads(urlopen(req, timeout=30).read().decode("utf-8"))


def get(path):
    req = Request(
        f"{BASE}{path}", headers={"Authorization": f"Bearer {TOKEN}"}, method="GET"
    )
    return json.loads(urlopen(req, timeout=30).read().decode("utf-8"))


def assert_contract(resp):
    assert isinstance(resp, dict), "Response must be a JSON object"
    for k in ("result", "provenance", "confidence", "alerts"):
        assert k in resp, f"Missing `{k}` in response"
    assert isinstance(resp["result"], dict), "`result` must be dict"
    assert isinstance(resp["provenance"], dict), "`provenance` must be dict"
    assert isinstance(resp["alerts"], list), "`alerts` must be list"
    assert isinstance(resp["confidence"], (int, float)), "`confidence` must be number"


def main():
    # Prime a simple search so /mcp/fetch has context
    try:
        post("/mcp/search", {"query": "mis pnl salary june 2025 formation"})
    except Exception:
        pass

    failures = []
    for case in logics:
        try:
            # Direct logic execution path: craft a plan with one logic id
            out = post(
                "/mcp/fetch",
                {"logic_id": case["logic_id"], "payload": case["payload"]},
            )
            # Endpoint returns a records wrapper in most code paths
            if "records" in out and isinstance(out["records"], list):
                content = out["records"][0].get("content")
                # content may be a mapping of logic_id -> result for logic-runner path
                if isinstance(content, dict) and case["logic_id"] in content:
                    resp = content[case["logic_id"]]
                else:
                    resp = content if isinstance(content, dict) else out
            else:
                resp = out
            assert_contract(resp)
            print(f"[OK] {case['logic_id']} -> contract shape valid")
        except (AssertionError, HTTPError, URLError, KeyError, ValueError) as e:
            failures.append((case["logic_id"], str(e)))
            print(f"[FAIL] {case['logic_id']}: {e}")
    if failures:
        print("\nFailures:")
        for lid, err in failures:
            print(f" - {lid}: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()

