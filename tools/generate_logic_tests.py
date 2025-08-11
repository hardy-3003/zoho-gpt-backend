#!/usr/bin/env python3
"""
Generate test scaffolds for all logic files.
"""

import os
import re
from pathlib import Path


def extract_logic_info(logic_file: Path) -> dict:
    """Extract basic information from a logic file."""
    with open(logic_file, "r") as f:
        content = f.read()

    # Extract logic number from filename
    match = re.search(r"logic_(\d+)_", logic_file.name)
    logic_num = match.group(1) if match else "000"

    # Try to extract LOGIC_META info
    logic_id = f"L-{logic_num.zfill(3)}"
    title = logic_file.stem.replace("_", " ").title()

    # Look for LOGIC_META in the file
    meta_match = re.search(r"LOGIC_META\s*=\s*{([^}]+)}", content)
    if meta_match:
        meta_content = meta_match.group(1)
        id_match = re.search(r'"id":\s*"([^"]+)"', meta_content)
        if id_match:
            logic_id = id_match.group(1)

        title_match = re.search(r'"title":\s*"([^"]+)"', meta_content)
        if title_match:
            title = title_match.group(1)

    return {
        "logic_num": logic_num,
        "logic_id": logic_id,
        "title": title,
        "filename": logic_file.stem,
    }


def generate_test_content(logic_info: dict) -> str:
    """Generate test content for a logic file."""
    logic_num = logic_info["logic_num"]
    logic_id = logic_info["logic_id"]
    title = logic_info["title"]
    filename = logic_info["filename"]

    return f'''"""
Test for {title} (Logic {logic_id}).

This test verifies the basic functionality and contract compliance of the {title} logic.
"""

import pytest
from logics.{filename} import handle, LOGIC_META


class TestLogic{logic_num}:
    """Test suite for {title} logic."""
    
    def test_logic_meta_structure(self):
        """Test that LOGIC_META has the required structure."""
        assert isinstance(LOGIC_META, dict)
        assert "id" in LOGIC_META
        assert "title" in LOGIC_META
        assert "tags" in LOGIC_META
        assert LOGIC_META["id"] == "{logic_id}"
        assert LOGIC_META["title"] == "{title}"
        assert isinstance(LOGIC_META["tags"], list)
    
    def test_handle_function_exists(self):
        """Test that the handle function exists and is callable."""
        assert callable(handle)
    
    def test_basic_contract_shape(self):
        """Test that the logic returns the expected contract shape."""
        payload = {{
            "org_id": "test_org",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "headers": {{}},
            "api_domain": "test.zoho.com",
            "query": "test query"
        }}
        
        result = handle(payload)
        
        # Verify basic contract structure
        assert isinstance(result, dict)
        assert "result" in result
        assert "provenance" in result
        assert "confidence" in result
        assert "alerts" in result
        assert "meta" in result
        
        # Verify data types
        assert isinstance(result["result"], dict)
        assert isinstance(result["provenance"], dict)
        assert isinstance(result["confidence"], (int, float))
        assert isinstance(result["alerts"], list)
        assert isinstance(result["meta"], dict)
        
        # Verify confidence is in valid range
        assert 0.0 <= result["confidence"] <= 1.0
        
        # Verify provenance has sources
        assert "sources" in result["provenance"]
        assert isinstance(result["provenance"]["sources"], list)
        
        # Verify meta has required fields
        assert "strategy" in result["meta"]
        assert "org_id" in result["meta"]
        assert result["meta"]["org_id"] == "test_org"
    
    def test_error_handling(self):
        """Test that the logic handles errors gracefully."""
        # Test with invalid payload
        payload = {{}}
        
        result = handle(payload)
        
        # Should still return valid contract shape
        assert isinstance(result, dict)
        assert "result" in result
        assert "provenance" in result
        assert "confidence" in result
        assert "alerts" in result
        assert "meta" in result
        
        # Should have lower confidence due to errors
        assert result["confidence"] < 0.8
    
    def test_period_validation(self):
        """Test that the logic validates date periods correctly."""
        # Test with invalid date range
        payload = {{
            "org_id": "test_org",
            "start_date": "2024-01-31",
            "end_date": "2024-01-01",  # End before start
            "headers": {{}},
            "api_domain": "test.zoho.com",
            "query": "test query"
        }}
        
        result = handle(payload)
        
        # Should handle invalid dates gracefully
        assert isinstance(result, dict)
        assert "alerts" in result
        # May or may not have date-related alerts depending on implementation
    
    def test_empty_result_handling(self):
        """Test that the logic handles empty results gracefully."""
        payload = {{
            "org_id": "test_org",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "headers": {{}},
            "api_domain": "test.zoho.com",
            "query": "test query"
        }}
        
        result = handle(payload)
        
        # Should return valid structure even with empty results
        assert isinstance(result["result"], dict)
        # Result may be empty but should still be a dict
'''


def create_test_directory(logic_num: str) -> Path:
    """Create test directory for a logic."""
    test_dir = Path(f"tests/unit/logic_{logic_num}")
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


def generate_all_tests():
    """Generate test scaffolds for all logic files."""
    logics_dir = Path("logics")
    generated_count = 0

    for logic_file in sorted(logics_dir.glob("logic_*.py")):
        try:
            logic_info = extract_logic_info(logic_file)
            logic_num = logic_info["logic_num"]

            # Create test directory
            test_dir = create_test_directory(logic_num)
            test_file = test_dir / f"test_logic_{logic_num}.py"

            # Skip if test already exists
            if test_file.exists():
                print(f"Skipped: {test_file} (already exists)")
                continue

            # Generate test content
            test_content = generate_test_content(logic_info)

            # Write test file
            with open(test_file, "w") as f:
                f.write(test_content)

            print(f"Generated: {test_file}")
            generated_count += 1

        except Exception as e:
            print(f"Error processing {logic_file}: {e}")

    print(f"\nGenerated {generated_count} test files")


if __name__ == "__main__":
    generate_all_tests()
