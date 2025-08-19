#!/usr/bin/env python3
"""Coverage audit script for justfile integration."""

import json
import pathlib


def main():
    p = pathlib.Path("artifacts/master_vs_repo_report.json")
    obj = json.loads(p.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                k: len(obj.get(k, []))
                for k in [
                    "missing_in_repo",
                    "extra_in_repo",
                    "slug_mismatches",
                    "path_mismatches",
                    "duplicate_ids",
                ]
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
