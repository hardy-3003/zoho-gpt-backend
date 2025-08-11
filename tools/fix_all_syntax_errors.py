#!/usr/bin/env python3
"""
Fix all remaining syntax and indentation errors in logic files.
"""

import os
import re
from pathlib import Path


def fix_logic_file(file_path: str) -> bool:
    """Fix all syntax and indentation issues in a logic file."""
    with open(file_path, "r") as f:
        content = f.read()

    original_content = content

    # Fix the pattern where get_json is not properly indented after try/except blocks
    # Pattern 1: except Exception: # pragma: no cover\n        def append_event...\n\n\n    def get_json
    pattern1 = r"(except Exception:\s*# pragma: no cover\s*)\n(\s*def append_event.*?return None\s*)\n\n\n(\s*def get_json.*?return {}\s*)"
    replacement1 = r"\1\n\2\n\n\3"
    content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)

    # Fix the pattern where return {} is not properly indented
    # Pattern 2: def get_json(...):\n        return {}
    pattern2 = r"(def get_json.*?:\s*)\n(\s*return {}\s*)"

    def fix_indentation(match):
        func_def = match.group(1)
        return_stmt = match.group(2)
        # Add proper indentation to return statement
        return func_def + "\n            return {}"

    content = re.sub(pattern2, fix_indentation, content, flags=re.DOTALL)

    # Fix the pattern where there's a return {} outside of a function
    # Pattern 3: except Exception: # pragma: no cover\n        def append_event...\n        return {}
    pattern3 = r"(except Exception:\s*# pragma: no cover\s*)\n(\s*def append_event.*?return None\s*)\n(\s*return {}\s*)"
    replacement3 = r"\1\n\2\n\n        def get_json(_url: str, headers: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore\n            return {}"
    content = re.sub(pattern3, replacement3, content, flags=re.DOTALL)

    # Fix the pattern where with_metrics is not properly indented
    # Pattern 4: except Exception: # pragma: no cover\n        def get_json...\n    def with_metrics
    pattern4 = r"(except Exception:\s*# pragma: no cover\s*)\n(\s*def get_json.*?return {}\s*)\n(\s*def with_metrics.*?:\s*)"
    replacement4 = r"\1\n\2\n\3"
    content = re.sub(pattern4, replacement4, content, flags=re.DOTALL)

    # Fix the pattern where with_metrics functions are not properly indented
    # Pattern 5: def with_metrics(name: str): # type: ignore\n        def deco(fn):\n            return fn\n        return deco
    pattern5 = r"(def with_metrics.*?:\s*)\n(\s*def deco.*?:\s*)\n(\s*return fn\s*)\n(\s*return deco\s*)"
    replacement5 = r"\1\n            def deco(fn):\n                return fn\n\n            return deco"
    content = re.sub(pattern5, replacement5, content, flags=re.DOTALL)

    # Fix the pattern where there are multiple get_json functions
    # Remove duplicate get_json functions that are not properly indented
    lines = content.split("\n")
    fixed_lines = []
    skip_next_get_json = False

    for i, line in enumerate(lines):
        if skip_next_get_json and line.strip().startswith("def get_json"):
            skip_next_get_json = False
            continue

        if line.strip().startswith("def get_json") and i > 0:
            prev_line = lines[i - 1].strip()
            if prev_line == "" and i > 1:
                prev_prev_line = lines[i - 2].strip()
                if prev_prev_line == "return None":
                    # This is a duplicate get_json after append_event, skip it
                    skip_next_get_json = True
                    continue

        fixed_lines.append(line)

    content = "\n".join(fixed_lines)

    if content != original_content:
        with open(file_path, "w") as f:
            f.write(content)
        print(f"Fixed: {file_path}")
        return True

    return False


def main():
    """Fix all logic files with syntax errors."""
    logics_dir = Path("logics")
    fixed_count = 0

    # List of files that are known to have issues based on test failures
    problem_files = [
        "logic_014_invoice_status.py",
        "logic_023_item_wise_profitability.py",
        "logic_036_month_on_month_comparison.py",
        "logic_041_tds_deducted_vs_paid.py",
        "logic_061_production_efficiency_report.py",
        "logic_081_outlier_expenses_detection.py",
        "logic_101_cash_reserve_advisor.py",
        "logic_121_manual_journal_suspicion_detector.py",
        "logic_142_transportation_cost_analysis.py",
        "logic_161_file_upload_to_entry_mapper_e_g_invoice_pdf_je.py",
        "logic_181_transaction_volume_spike_alert.py",
    ]

    # First fix the known problem files
    for filename in problem_files:
        file_path = logics_dir / filename
        if file_path.exists():
            if fix_logic_file(str(file_path)):
                fixed_count += 1

    # Then fix all other logic files
    for logic_file in logics_dir.glob("logic_*.py"):
        if logic_file.name not in problem_files:
            if fix_logic_file(str(logic_file)):
                fixed_count += 1

    print(f"Fixed {fixed_count} files")


if __name__ == "__main__":
    main()
