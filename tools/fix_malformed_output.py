#!/usr/bin/env python3
"""
Fix malformed output where return {} and try: got concatenated.
"""

import os
import re
from pathlib import Path


def fix_logic_file(file_path: str) -> bool:
    """Fix malformed output in a logic file."""
    with open(file_path, "r") as f:
        content = f.read()

    original_content = content

    # Fix the pattern where return {} and try: got concatenated
    # Pattern: return {}try:
    pattern1 = r"return \{\}try:"
    replacement1 = r"return {}\n\ntry:"
    content = re.sub(pattern1, replacement1, content)

    # Fix the pattern where return {} and LOGIC_META got concatenated
    # Pattern: return {}LOGIC_META
    pattern2 = r"return \{\}LOGIC_META"
    replacement2 = r"return {}\n\nLOGIC_META"
    content = re.sub(pattern2, replacement2, content)

    # Fix the pattern where return {} is outside a function
    # Pattern: except Exception: # pragma: no cover\n        return {}
    pattern3 = r"(except Exception:\s*# pragma: no cover\s*)\n(\s*return \{\}\s*)"
    replacement3 = r"\1\n        def get_json(_url: str, headers: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore\n            return {}"
    content = re.sub(pattern3, replacement3, content)

    if content != original_content:
        with open(file_path, "w") as f:
            f.write(content)
        print(f"Fixed: {file_path}")
        return True

    return False


def main():
    """Fix all logic files with malformed output."""
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
        "logic_141_on_time_delivery_rate.py",
        "logic_161_file_upload_to_entry_mapper_e_g_invoice_pdf_je.py",
        "logic_181_transaction_volume_spike_alert.py",
    ]

    # Fix the known problem files
    for filename in problem_files:
        file_path = logics_dir / filename
        if file_path.exists():
            if fix_logic_file(str(file_path)):
                fixed_count += 1

    print(f"Fixed {fixed_count} files")


if __name__ == "__main__":
    main()
