#!/usr/bin/env python3
"""
Golden generator: rebuild expected.json for golden fixtures deterministically.

Usage:
  python tools/gen_golden.py              # rebuild all cases
  python tools/gen_golden.py --case NAME  # rebuild just one case (dir name)
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Any

from fastapi.testclient import TestClient

# Local imports via main app
from main import app


FIXTURES_ROOT = Path(__file__).parent.parent / "tests" / "golden" / "fixtures"


def rebuild_case(case_name: str) -> None:
    case_dir = FIXTURES_ROOT / case_name
    if not (case_dir / "input.json").exists():
        raise FileNotFoundError(f"Missing input.json for case '{case_name}'")

    with open(case_dir / "input.json", "r") as f:
        request_json: Dict[str, Any] = json.load(f)

    client = TestClient(app)
    resp = client.post("/api/execute", json=request_json)
    if resp.status_code != 200:
        raise RuntimeError(f"/api/execute failed for {case_name}: {resp.text}")

    expected = resp.json()
    with open(case_dir / "expected.json", "w") as f:
        json.dump(expected, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Rebuilt golden for case: {case_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild golden expected.json files")
    parser.add_argument(
        "--case", dest="case", help="Specific case name to rebuild", default=None
    )
    args = parser.parse_args()

    if args.case:
        rebuild_case(args.case)
        return

    # Rebuild all
    if not FIXTURES_ROOT.exists():
        print("No golden fixtures directory found; nothing to do")
        return

    for p in sorted(FIXTURES_ROOT.iterdir()):
        if p.is_dir() and (p / "input.json").exists():
            rebuild_case(p.name)


if __name__ == "__main__":
    main()
