#!/usr/bin/env python3
"""
Cleanup script for Phase 2 temporary files.

This script removes temporary files and artifacts created during Phase 2 implementation.
"""

import os
import shutil
from pathlib import Path


def cleanup_temp_files():
    """Remove temporary files created during Phase 2."""
    temp_files = [
        "tools/fix_syntax_errors.py",
        "tools/fix_indentation.py",
        "tools/fix_all_indentation.py",
        "tools/fix_remaining_indentation.py",
        "tools/fix_final_indentation.py",
        "tools/fix_specific_indentation.py",
        "tools/fix_malformed_output.py",
        "tools/fix_remaining_syntax.py",
    ]

    removed_count = 0
    for temp_file in temp_files:
        if Path(temp_file).exists():
            os.remove(temp_file)
            print(f"Removed: {temp_file}")
            removed_count += 1

    return removed_count


def cleanup_backup_files():
    """Remove backup files created during fixes."""
    logics_dir = Path("logics")
    backup_files = list(logics_dir.glob("*.bak*"))

    removed_count = 0
    for backup_file in backup_files:
        os.remove(backup_file)
        print(f"Removed: {backup_file}")
        removed_count += 1

    return removed_count


def cleanup_cache_directories():
    """Remove cache directories."""
    cache_dirs = [
        "__pycache__",
        "logics/__pycache__",
        "tests/__pycache__",
        "tests/unit/__pycache__",
        "tests/integration/__pycache__",
        "tests/performance/__pycache__",
    ]

    removed_count = 0
    for cache_dir in cache_dirs:
        if Path(cache_dir).exists():
            shutil.rmtree(cache_dir)
            print(f"Removed: {cache_dir}")
            removed_count += 1

    return removed_count


def main():
    """Main cleanup function."""
    print("🧹 PHASE 2 CLEANUP")
    print("Removing temporary files and artifacts...")

    # Cleanup temporary files
    temp_count = cleanup_temp_files()

    # Cleanup backup files
    backup_count = cleanup_backup_files()

    # Cleanup cache directories
    cache_count = cleanup_cache_directories()

    total_removed = temp_count + backup_count + cache_count

    print(f"\n✅ CLEANUP COMPLETED")
    print(f"Removed {temp_count} temporary files")
    print(f"Removed {backup_count} backup files")
    print(f"Removed {cache_count} cache directories")
    print(f"Total: {total_removed} items cleaned up")

    if total_removed == 0:
        print("No cleanup needed - no temporary files found")


if __name__ == "__main__":
    main()
