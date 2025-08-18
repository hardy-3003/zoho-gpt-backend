from __future__ import annotations

import sys
import pathlib
import re
from typing import List


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    bad = re.compile(
        r"^(?:from|import)\s+(subprocess|socket|requests|urllib\.request|os)\b", re.M
    )
    offenders: List[str] = []
    for p in [root / "logics", root / "app", root / "cli"]:
        if p.exists():
            for f in p.rglob("*.py"):
                try:
                    s = f.read_text(errors="ignore")
                except Exception:
                    continue
                if bad.search(s):
                    offenders.append(str(f))
    print({"offenders": offenders})
    return 0 if not offenders else 3


if __name__ == "__main__":
    sys.exit(main())
