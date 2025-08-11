#!/usr/bin/env python3
"""
Script to fix syntax errors in logic files caused by meta field addition.
"""

import os
import re
import glob


def fix_syntax_errors_in_file(filepath):
    """Fix syntax errors in a single file."""
    with open(filepath, "r") as f:
        content = f.read()

    # Fix the malformed output dictionary pattern
    pattern = r'(\s+output = \{\s*\n(?:\s+"[^"]+": [^,\n]+,\n)*\s*,\s*\n\s+"meta": LOGIC_META,\s*\n\s*\})'

    match = re.search(pattern, content, re.MULTILINE)
    if match:
        old_output = match.group(1)
        # Remove the extra comma and fix formatting
        new_output = re.sub(r',\s*\n\s*"meta":', ',\n        "meta":', old_output)
        new_output = re.sub(r',\s*\n\s*"meta":', ',\n        "meta":', new_output)

        # Replace in content
        new_content = content.replace(old_output, new_output)

        # Write back to file
        with open(filepath, "w") as f:
            f.write(new_content)

        return True

    return False


def main():
    """Main function to fix syntax errors in all logic files."""
    logic_files = glob.glob("logics/logic_*.py")

    fixed_count = 0
    for filepath in logic_files:
        if fix_syntax_errors_in_file(filepath):
            print(f"Fixed syntax: {filepath}")
            fixed_count += 1

    print(f"\nTotal files fixed: {fixed_count}")


if __name__ == "__main__":
    main()
