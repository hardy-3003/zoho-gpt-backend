"""
Golden Test Runner

Discovers cases under tests/golden/fixtures/<case>/input.json,
executes the contract-only /api/execute, and compares against
expected.json with a crisp diff and actionable hints.
"""

import json
from pathlib import Path
from typing import Dict, Any, List

import pytest
from fastapi.testclient import TestClient

from main import app
from tools.json_compare import compare_json


FIXTURES_ROOT = Path(__file__).parent / "fixtures"
DIFFS_ROOT = Path(__file__).parent / "diffs"


def discover_cases() -> List[str]:
    cases: List[str] = []
    if not FIXTURES_ROOT.exists():
        return cases
    for p in FIXTURES_ROOT.iterdir():
        if p.is_dir() and (p / "input.json").exists():
            cases.append(p.name)
    return sorted(cases)


@pytest.mark.golden
@pytest.mark.parametrize("case_name", discover_cases())
def test_golden_case(case_name: str) -> None:
    client = TestClient(app)
    case_dir = FIXTURES_ROOT / case_name

    with open(case_dir / "input.json", "r") as f:
        request_json: Dict[str, Any] = json.load(f)

    # Execute via REST contract surface
    resp = client.post("/api/execute", json=request_json)
    assert resp.status_code == 200, f"/api/execute failed: {resp.text}"
    actual: Dict[str, Any] = resp.json()

    # Load expected golden
    with open(case_dir / "expected.json", "r") as f:
        expected: Dict[str, Any] = json.load(f)

    # Compare (strict by default); tolerances/ignores can be extended later
    equal, diff_text = compare_json(expected, actual)
    if not equal:
        DIFFS_ROOT.mkdir(parents=True, exist_ok=True)
        diff_file = DIFFS_ROOT / f"{case_name}.diff"
        with open(diff_file, "w") as df:
            df.write(diff_text)

        pytest.fail(
            "\n".join(
                [
                    f"Golden drift detected for case '{case_name}'.",
                    f"Diff written to: {diff_file}",
                    "If intentional, rebuild goldens:",
                    "  just golden-rebuild CASE=" + case_name,
                    "Or rebuild all:",
                    "  just golden-rebuild",
                ]
            )
        )
