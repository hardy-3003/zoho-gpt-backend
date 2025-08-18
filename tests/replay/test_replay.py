"""
Replay tests: iterate over fixtures and assert canonical hash equality.

On mismatch, diffs are written by the replay runner under tests/replay/diffs/<case>/.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from tools.replay_runner import discover_cases, run_case


@pytest.mark.golden
def test_replay_all_cases():
    cases = discover_cases()
    assert (
        cases
    ), "No replay cases discovered. Add fixtures under tests/replay/fixtures/<case>/"
    failures: list[str] = []
    for case in cases:
        ok = run_case(case, write_diff_on_mismatch=True)
        if not ok:
            failures.append(case)
    assert not failures, f"Replay mismatches for cases: {', '.join(failures)}"
