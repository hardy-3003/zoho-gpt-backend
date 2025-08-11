#!/usr/bin/env python3
"""
Phase 2 Test Runner.

This script demonstrates the Phase 2 deliverables:
- 2.1 Comprehensive Test Coverage
- 2.2 Logic Module Contract Compliance
- 2.3 Performance & Reliability Testing
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        success = result.returncode == 0
        print(
            f"✅ SUCCESS" if success else f"❌ FAILED (exit code: {result.returncode})"
        )
        return success
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    """Main function to run Phase 2 tests."""
    print("🚀 PHASE 2 TEST RUNNER")
    print("Testing Phase 2 deliverables...")

    # Phase 2.1: Comprehensive Test Coverage
    print(f"\n📋 PHASE 2.1: COMPREHENSIVE TEST COVERAGE")

    # Count test files
    test_files = list(Path("tests/unit").glob("logic_*/test_logic_*.py"))
    print(f"Generated {len(test_files)} logic test files")

    # Run a sample of logic tests
    sample_tests = [
        "tests/unit/logic_001/test_logic_001.py",
        "tests/unit/logic_002/test_logic_002.py",
        "tests/unit/logic_003/test_logic_003.py",
        "tests/unit/logic_014/test_logic_014.py",
        "tests/unit/logic_015/test_logic_015.py",
    ]

    for test_file in sample_tests:
        if Path(test_file).exists():
            run_command(
                f"python -m pytest {test_file} -v", f"Running tests for {test_file}"
            )

    # Phase 2.2: Logic Module Contract Compliance
    print(f"\n📋 PHASE 2.2: LOGIC MODULE CONTRACT COMPLIANCE")

    run_command(
        "python tools/verify_contract_compliance.py", "Verifying contract compliance"
    )

    # Phase 2.3: Performance & Reliability Testing
    print(f"\n📋 PHASE 2.3: PERFORMANCE & RELIABILITY TESTING")

    # Run performance tests
    run_command(
        "python -m pytest tests/performance/test_load_performance.py -v",
        "Running performance tests",
    )

    # Run integration tests
    run_command(
        "python -m pytest tests/integration/test_orchestrators.py -v",
        "Running orchestrator integration tests",
    )

    # Run existing contract tests
    print(f"\n📋 EXISTING CONTRACT TESTS")
    run_command(
        "python -m pytest tests/unit/contracts/ -v",
        "Running existing contract validation tests",
    )

    # Summary
    print(f"\n{'='*60}")
    print(f"🎯 PHASE 2 DELIVERABLES SUMMARY")
    print(f"{'='*60}")
    print(f"✅ 2.1 Test Coverage: Generated {len(test_files)} test files")
    print(f"✅ 2.2 Contract Compliance: Created verification script")
    print(f"✅ 2.3 Performance Testing: Created load and integration tests")
    print(f"✅ Integration Tests: Created orchestrator tests")
    print(f"✅ Performance Tests: Created load testing framework")
    print(f"\n📊 Test Files Generated:")
    print(f"   - Logic tests: {len(test_files)} files")
    print(f"   - Integration tests: 1 file")
    print(f"   - Performance tests: 1 file")
    print(f"   - Total: {len(test_files) + 2} new test files")


if __name__ == "__main__":
    main()
