from __future__ import annotations

import json
import sys
import pathlib
import hashlib


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    master_path = root / "artifacts/master_index.json"
    if not master_path.exists():
        print(json.dumps({"error": "missing_master_index"}, sort_keys=True))
        return 3

    master = json.loads(master_path.read_text(encoding="utf-8"))

    # Stub policy: require at least one of the seed logics to be referenced in tests/fixtures
    seeds = {"logic_001_profit_and_loss_summary", "logic_231_ratio_impact_advisor"}
    seen: set[str] = set()

    tests_dir = root / "tests"
    for p in tests_dir.rglob("*.json"):
        try:
            s = p.read_text(errors="ignore")
        except Exception:
            continue
        for k in seeds:
            if k in s:
                seen.add(k)

    ok = len(seen) >= 1
    print(json.dumps({"seed_coverage": sorted(seen), "policy_ok": ok}, sort_keys=True))
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
