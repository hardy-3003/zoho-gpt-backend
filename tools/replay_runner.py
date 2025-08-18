"""
Evidence Replay Runner

Task P1.3.4 — Evidence Replay “Golden” Runner

Capabilities:
- Load a manifest describing a prior run (ExecuteRequest + evidence refs)
- Recompute ExecuteResponse via FastAPI TestClient (no external I/O)
- Compute canonical JSON and sha256
- Compare with expected hash; write diffs on mismatch

CLI:
- python -m tools.replay_runner run --case <name>
- python -m tools.replay_runner freeze --case <name>
- python -m tools.replay_runner run-all
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

from fastapi.testclient import TestClient

# Ensure project root is on sys.path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import app  # noqa: E402
from tools.hash_utils import (
    to_canonical_json,
    canonical_sha256_of_obj,
    write_pretty_json,
)  # noqa: E402


FIXTURES_DIR = PROJECT_ROOT / "tests" / "replay" / "fixtures"
DIFFS_DIR = PROJECT_ROOT / "tests" / "replay" / "diffs"


def _read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    return _read_json(manifest_path)


def _coerce_dataclasses(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return {k: _coerce_dataclasses(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_coerce_dataclasses(v) for v in obj]
    return obj


def compute_response_and_hash(
    input_payload: Dict[str, Any],
) -> Tuple[Dict[str, Any], str, str]:
    client = TestClient(app)
    resp = client.post("/api/execute", json=input_payload)
    status = resp.status_code
    try:
        obj = resp.json()
    except Exception:
        obj = {"error": "non-json-response", "text": resp.text}
    coerced = _coerce_dataclasses(obj)
    canonical = to_canonical_json(coerced)
    digest = canonical_sha256_of_obj(coerced)
    return coerced, canonical, digest


def _fixture_paths(case: str) -> Dict[str, Path]:
    case_dir = FIXTURES_DIR / case
    return {
        "dir": case_dir,
        "manifest": case_dir / "manifest.json",
        "input": case_dir / "input.json",
        "expected_hash": case_dir / "expected_hash.txt",
    }


def run_case(case: str, write_diff_on_mismatch: bool = True) -> bool:
    paths = _fixture_paths(case)
    manifest = load_manifest(paths["manifest"])
    # Load ExecuteRequest
    input_path = (paths["dir"] / manifest["input_path"]).resolve()
    input_payload = _read_json(input_path)

    observed_obj, canonical_json, observed_hash = compute_response_and_hash(
        input_payload
    )

    # Read expected
    expected_hash = ""
    if paths["expected_hash"].exists():
        expected_hash = paths["expected_hash"].read_text(encoding="utf-8").strip()

    matched = expected_hash == observed_hash and len(expected_hash) == 64
    if not matched and write_diff_on_mismatch:
        DIFFS_DIR.mkdir(parents=True, exist_ok=True)
        # Write observed JSON and info
        out_dir = DIFFS_DIR / case
        out_dir.mkdir(parents=True, exist_ok=True)
        write_pretty_json(str(out_dir / "observed.json"), observed_obj)
        (out_dir / "observed.hash").write_text(observed_hash + "\n", encoding="utf-8")
        (out_dir / "expected.hash").write_text(
            (expected_hash or "<missing>") + "\n", encoding="utf-8"
        )
        # Simple hint file
        hint = (
            "Replay mismatch detected.\n"
            f"Case: {case}\n"
            f"Observed SHA256: {observed_hash}\n"
            f"Expected SHA256: {expected_hash or '<missing>'}\n\n"
            "To update frozen hash intentionally, run: just replay-freeze CASE="
            + case
            + "\n"
        )
        (out_dir / "HINT.txt").write_text(hint, encoding="utf-8")
    return matched


def freeze_case(case: str) -> str:
    paths = _fixture_paths(case)
    manifest = load_manifest(paths["manifest"])
    input_path = (paths["dir"] / manifest["input_path"]).resolve()
    input_payload = _read_json(input_path)
    _, _, observed_hash = compute_response_and_hash(input_payload)
    paths["expected_hash"].write_text(observed_hash + "\n", encoding="utf-8")
    return observed_hash


def discover_cases() -> list[str]:
    if not FIXTURES_DIR.exists():
        return []
    return sorted(
        [p.name for p in FIXTURES_DIR.iterdir() if (p / "manifest.json").exists()]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evidence Replay Runner")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run a single replay case")
    p_run.add_argument("--case", required=True)

    p_freeze = sub.add_parser("freeze", help="Freeze expected hash for a case")
    p_freeze.add_argument("--case", required=True)

    sub.add_parser("run-all", help="Run all replay cases")

    args = parser.parse_args(argv)

    if args.cmd == "run":
        ok = run_case(args.case, write_diff_on_mismatch=True)
        print("OK" if ok else "MISMATCH")
        return 0 if ok else 2
    if args.cmd == "freeze":
        h = freeze_case(args.case)
        print(h)
        return 0
    if args.cmd == "run-all":
        cases = discover_cases()
        any_fail = False
        for c in cases:
            ok = run_case(c, write_diff_on_mismatch=True)
            print(f"{c}: {'OK' if ok else 'MISMATCH'}")
            any_fail = any_fail or (not ok)
        return 0 if not any_fail else 2

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
