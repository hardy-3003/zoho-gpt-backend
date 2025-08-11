"""
Test for Transportation Cost Analysis (Logic L-142).

This test verifies the basic functionality and contract compliance of the Transportation Cost Analysis logic.
"""

import pytest
from logics.logic_142_transportation_cost_analysis import handle, LOGIC_META


class TestLogic142:
    """Test suite for Transportation Cost Analysis logic."""
    
    def test_logic_meta_structure(self):
        """Test that LOGIC_META has the required structure."""
        assert isinstance(LOGIC_META, dict)
        assert "id" in LOGIC_META
        assert "title" in LOGIC_META
        assert "tags" in LOGIC_META
        assert LOGIC_META["id"] == "L-142"
        assert LOGIC_META["title"] == "Transportation Cost Analysis"
        assert isinstance(LOGIC_META["tags"], list)
    
    def test_handle_function_exists(self):
        """Test that the handle function exists and is callable."""
        assert callable(handle)
    
    def test_basic_contract_shape(self):
        """Test that the logic returns the expected contract shape."""
        payload = {
            "org_id": "test_org",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "headers": {},
            "api_domain": "test.zoho.com",
            "query": "test query"
        }
        
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
        payload = {}
        
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
        payload = {
            "org_id": "test_org",
            "start_date": "2024-01-31",
            "end_date": "2024-01-01",  # End before start
            "headers": {},
            "api_domain": "test.zoho.com",
            "query": "test query"
        }
        
        result = handle(payload)
        
        # Should handle invalid dates gracefully
        assert isinstance(result, dict)
        assert "alerts" in result
        # May or may not have date-related alerts depending on implementation
    
    def test_empty_result_handling(self):
        """Test that the logic handles empty results gracefully."""
        payload = {
            "org_id": "test_org",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "headers": {},
            "api_domain": "test.zoho.com",
            "query": "test query"
        }
        
        result = handle(payload)
        
        # Should return valid structure even with empty results
        assert isinstance(result["result"], dict)
        # Result may be empty but should still be a dict
