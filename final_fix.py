#!/usr/bin/env python3
"""
Final fix for remaining syntax errors in logic files.
"""

import os
import re
from pathlib import Path


def fix_duplicate_try_statements(file_path: str) -> bool:
    """Fix duplicate try statements in a single logic file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if file has duplicate try statements
        if "try:\ntry:" in content:
            # Fix duplicate try statements
            content = re.sub(r"try:\s*\ntry:", "try:", content)

            # Write back the fixed content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"Fixed duplicate try: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    """Fix duplicate try statements in all logic files."""
    logics_dir = Path("logics")
    if not logics_dir.exists():
        print("logics directory not found")
        return

    fixed_count = 0
    total_files = 0

    for logic_file in logics_dir.glob("logic_*.py"):
        total_files += 1
        if fix_duplicate_try_statements(str(logic_file)):
            fixed_count += 1

    print(f"\nSummary:")
    print(f"Total logic files checked: {total_files}")
    print(f"Files fixed: {fixed_count}")
    print(f"Files with no issues: {total_files - fixed_count}")


if __name__ == "__main__":
    main()
