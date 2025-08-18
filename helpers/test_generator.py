"""
Test Generation System for Auto-Expansion Capabilities

This module provides automated test generation capabilities for creating
test scaffolding and test cases for generated logic modules.

Features:
- Automated test scaffolding with template generation
- Test case generation based on logic parameters
- Test validation and execution framework
- Test maintenance and evolution tracking
- Test coverage analysis and reporting
"""

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from helpers.history_store import write_event
from helpers.logic_generator import GeneratedLogic

logger = logging.getLogger(__name__)


@dataclass
class GeneratedTest:
    """Represents a generated test module."""

    test_id: str
    logic_id: str
    test_name: str
    test_code: str
    test_cases: List[Dict[str, Any]]
    validation_results: Dict[str, Any]
    coverage_score: float
    quality_score: float
    creation_date: datetime
    status: str  # 'draft', 'validated', 'active', 'deprecated'
    metadata: Dict[str, Any]


class TestGenerator:
    """Test generation system for auto-expansion capabilities."""

    def __init__(self, storage_path: str = "data/test_generation/"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.generated_file = self.storage_path / "generated_tests.json"
        self.generated_tests: Dict[str, GeneratedTest] = {}
        self._load_data()

        self.quality_threshold = 0.7
        self.coverage_threshold = 0.8
        self.generation_count = 0
        self.success_count = 0

    def _load_data(self) -> None:
        """Load existing test generation data."""
        try:
            if self.generated_file.exists():
                with open(self.generated_file, "r") as f:
                    data = json.load(f)
                    for test_data in data.get("generated_tests", []):
                        test = self._dict_to_generated_test(test_data)
                        self.generated_tests[test.test_id] = test
            logger.info(f"Loaded {len(self.generated_tests)} generated tests")
        except Exception as e:
            logger.error(f"Error loading test generation data: {e}")

    def _save_data(self) -> None:
        """Save test generation data."""
        try:
            generated_data = {
                "generated_tests": [
                    asdict(test) for test in self.generated_tests.values()
                ],
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.generated_file, "w") as f:
                json.dump(generated_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving test generation data: {e}")

    def _dict_to_generated_test(self, data: Dict[str, Any]) -> GeneratedTest:
        """Convert dictionary to GeneratedTest."""
        return GeneratedTest(
            test_id=data["test_id"],
            logic_id=data["logic_id"],
            test_name=data["test_name"],
            test_code=data["test_code"],
            test_cases=data["test_cases"],
            validation_results=data["validation_results"],
            coverage_score=data["coverage_score"],
            quality_score=data["quality_score"],
            creation_date=datetime.fromisoformat(data["creation_date"]),
            status=data["status"],
            metadata=data["metadata"],
        )

    def generate_test(self, generated_logic: GeneratedLogic) -> GeneratedTest:
        """Generate test for a generated logic."""
        try:
            # Generate test code
            test_code = self._generate_test_code(generated_logic)

            # Generate test cases
            test_cases = self._generate_test_cases(generated_logic)

            # Validate generated test
            validation_results = self._validate_generated_test(test_code, test_cases)

            # Calculate scores
            coverage_score = self._calculate_coverage_score(test_cases, generated_logic)
            quality_score = self._calculate_quality_score(
                validation_results, coverage_score
            )

            # Create generated test
            test_id = self._generate_test_id(generated_logic)
            test_name = self._generate_test_name(generated_logic)

            generated_test = GeneratedTest(
                test_id=test_id,
                logic_id=generated_logic.logic_id,
                test_name=test_name,
                test_code=test_code,
                test_cases=test_cases,
                validation_results=validation_results,
                coverage_score=coverage_score,
                quality_score=quality_score,
                creation_date=datetime.now(),
                status=(
                    "draft" if quality_score < self.quality_threshold else "validated"
                ),
                metadata={
                    "logic_id": generated_logic.logic_id,
                    "generation_method": "auto_generated",
                },
            )

            # Store generated test
            self.generated_tests[test_id] = generated_test

            # Update statistics
            self.generation_count += 1
            if quality_score >= self.quality_threshold:
                self.success_count += 1

            # Save data
            self._save_data()

            # Record event
            write_event(
                "test_generated",
                {
                    "test_id": test_id,
                    "logic_id": generated_logic.logic_id,
                    "quality_score": quality_score,
                    "coverage_score": coverage_score,
                },
            )

            logger.info(
                f"Generated test {test_id} with quality score {quality_score:.2f}"
            )
            return generated_test

        except Exception as e:
            logger.error(f"Failed to generate test: {e}")
            raise

    def _generate_test_code(self, generated_logic: GeneratedLogic) -> str:
        """Generate test code for logic."""
        test_name = self._generate_test_name(generated_logic)
        logic_name = generated_logic.logic_name

        test_code = f'''
"""
Test for {logic_name}
Generated automatically for logic {generated_logic.logic_id}
"""

import pytest
from typing import Dict, Any
from unittest.mock import patch, MagicMock

# Import the generated logic
from logics.{generated_logic.logic_id.lower()} import handle, LOGIC_ID, LOGIC_META

class Test{test_name}:
    """Test cases for {logic_name}."""
    
    def test_logic_metadata(self):
        """Test that logic has proper metadata."""
        assert LOGIC_ID == "{generated_logic.logic_id}"
        assert LOGIC_META["id"] == "{generated_logic.logic_id}"
        assert LOGIC_META["name"] == "{logic_name}"
        assert "category" in LOGIC_META
        assert "version" in LOGIC_META
        
    def test_handle_function_exists(self):
        """Test that handle function exists and is callable."""
        assert callable(handle)
        
    def test_basic_functionality(self):
        """Test basic functionality with valid input."""
        payload = {{
            "data_source": "{generated_logic.parameters.get("data_source", "test_data")}",
            "analysis_type": "{generated_logic.parameters.get("analysis_type", "general")}"
        }}
        
        result = handle(payload)
        
        assert isinstance(result, dict)
        assert "result" in result
        assert "provenance" in result
        assert "confidence" in result
        assert "alerts" in result
        
    def test_error_handling(self):
        """Test error handling with invalid input."""
        payload = {{}}  # Empty payload
        
        result = handle(payload)
        
        assert isinstance(result, dict)
        assert "result" in result
        assert "alerts" in result
        assert isinstance(result["alerts"], list)
        
    def test_parameter_validation(self):
        """Test parameter validation."""
        # Test with missing required parameters
        payload = {{"invalid_param": "value"}}
        
        result = handle(payload)
        
        assert isinstance(result, dict)
        assert "alerts" in result
        
    def test_confidence_scoring(self):
        """Test that confidence scores are reasonable."""
        payload = {{
            "data_source": "{generated_logic.parameters.get("data_source", "test_data")}",
            "analysis_type": "{generated_logic.parameters.get("analysis_type", "general")}"
        }}
        
        result = handle(payload)
        
        assert "confidence" in result
        confidence = result["confidence"]
        assert isinstance(confidence, (int, float))
        assert 0.0 <= confidence <= 1.0
        
    def test_provenance_tracking(self):
        """Test that provenance information is included."""
        payload = {{
            "data_source": "{generated_logic.parameters.get("data_source", "test_data")}",
            "analysis_type": "{generated_logic.parameters.get("analysis_type", "general")}"
        }}
        
        result = handle(payload)
        
        assert "provenance" in result
        provenance = result["provenance"]
        assert isinstance(provenance, dict)
        assert "data_source" in provenance
        assert "analysis_type" in provenance
        
    def test_alert_handling(self):
        """Test that alerts are properly formatted."""
        payload = {{
            "data_source": "{generated_logic.parameters.get("data_source", "test_data")}",
            "analysis_type": "{generated_logic.parameters.get("analysis_type", "general")}"
        }}
        
        result = handle(payload)
        
        assert "alerts" in result
        alerts = result["alerts"]
        assert isinstance(alerts, list)
        
    @patch('helpers.learning_hooks.record_feedback')
    def test_learning_hooks_integration(self, mock_record_feedback):
        """Test integration with learning hooks."""
        payload = {{
            "data_source": "{generated_logic.parameters.get("data_source", "test_data")}",
            "analysis_type": "{generated_logic.parameters.get("analysis_type", "general")}"
        }}
        
        result = handle(payload)
        
        # Verify that learning hooks are called
        mock_record_feedback.assert_called()
        
    @patch('helpers.history_store.write_event')
    def test_history_integration(self, mock_write_event):
        """Test integration with history store."""
        payload = {{
            "data_source": "{generated_logic.parameters.get("data_source", "test_data")}",
            "analysis_type": "{generated_logic.parameters.get("analysis_type", "general")}"
        }}
        
        result = handle(payload)
        
        # Verify that history events are written
        mock_write_event.assert_called()
        
    def test_performance_characteristics(self):
        """Test performance characteristics."""
        import time
        
        payload = {{
            "data_source": "{generated_logic.parameters.get("data_source", "test_data")}",
            "analysis_type": "{generated_logic.parameters.get("analysis_type", "general")}"
        }}
        
        start_time = time.time()
        result = handle(payload)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (5 seconds)
        assert execution_time < 5.0
        
    def test_memory_usage(self):
        """Test memory usage characteristics."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        payload = {{
            "data_source": "{generated_logic.parameters.get("data_source", "test_data")}",
            "analysis_type": "{generated_logic.parameters.get("analysis_type", "general")}"
        }}
        
        # Run multiple times to check for memory leaks
        for _ in range(10):
            result = handle(payload)
            
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 10MB)
        assert memory_increase < 10 * 1024 * 1024
'''

        return test_code

    def _generate_test_cases(
        self, generated_logic: GeneratedLogic
    ) -> List[Dict[str, Any]]:
        """Generate test cases for logic."""
        test_cases = []

        # Basic functionality test case
        test_cases.append(
            {
                "name": "basic_functionality",
                "description": "Test basic functionality with valid input",
                "input": {
                    "data_source": generated_logic.parameters.get(
                        "data_source", "test_data"
                    ),
                    "analysis_type": generated_logic.parameters.get(
                        "analysis_type", "general"
                    ),
                },
                "expected_output": {
                    "result": "dict",
                    "provenance": "dict",
                    "confidence": "float",
                    "alerts": "list",
                },
                "validation_rules": [
                    "output_has_required_fields",
                    "confidence_in_valid_range",
                    "alerts_is_list",
                ],
            }
        )

        # Error handling test case
        test_cases.append(
            {
                "name": "error_handling",
                "description": "Test error handling with invalid input",
                "input": {},
                "expected_output": {"result": "any", "alerts": "list"},
                "validation_rules": ["output_has_alerts", "alerts_is_list"],
            }
        )

        # Parameter validation test case
        test_cases.append(
            {
                "name": "parameter_validation",
                "description": "Test parameter validation",
                "input": {"invalid_param": "value"},
                "expected_output": {"alerts": "list"},
                "validation_rules": ["output_has_alerts"],
            }
        )

        # Performance test case
        test_cases.append(
            {
                "name": "performance_test",
                "description": "Test performance characteristics",
                "input": {
                    "data_source": generated_logic.parameters.get(
                        "data_source", "test_data"
                    ),
                    "analysis_type": generated_logic.parameters.get(
                        "analysis_type", "general"
                    ),
                },
                "expected_output": {"execution_time": "float"},
                "validation_rules": ["execution_time_under_threshold"],
            }
        )

        return test_cases

    def _validate_generated_test(
        self, test_code: str, test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate generated test code."""
        validation_results = {
            "syntax_valid": True,
            "has_test_class": True,
            "has_test_methods": True,
            "has_assertions": True,
            "has_mocking": True,
            "has_documentation": True,
            "alerts": [],
        }

        # Check syntax
        try:
            compile(test_code, "<generated_test>", "exec")
        except SyntaxError as e:
            validation_results["syntax_valid"] = False
            validation_results["alerts"].append(f"Syntax error: {e}")

        # Check for test class
        if "class Test" not in test_code:
            validation_results["has_test_class"] = False
            validation_results["alerts"].append("Missing test class")

        # Check for test methods
        if "def test_" not in test_code:
            validation_results["has_test_methods"] = False
            validation_results["alerts"].append("Missing test methods")

        # Check for assertions
        if "assert " not in test_code:
            validation_results["has_assertions"] = False
            validation_results["alerts"].append("Missing assertions")

        # Check for mocking
        if "@patch" not in test_code and "unittest.mock" not in test_code:
            validation_results["has_mocking"] = False
            validation_results["alerts"].append("Missing mocking setup")

        # Check for documentation
        if '"""' not in test_code:
            validation_results["has_documentation"] = False
            validation_results["alerts"].append("Missing documentation")

        return validation_results

    def _calculate_coverage_score(
        self, test_cases: List[Dict[str, Any]], generated_logic: GeneratedLogic
    ) -> float:
        """Calculate coverage score for generated test."""
        # Base coverage from test cases
        base_coverage = len(test_cases) / 10.0  # Normalize to 10 test cases

        # Coverage for different aspects
        aspects_covered = 0
        total_aspects = 5

        # Check if basic functionality is covered
        if any("basic_functionality" in case["name"] for case in test_cases):
            aspects_covered += 1

        # Check if error handling is covered
        if any("error_handling" in case["name"] for case in test_cases):
            aspects_covered += 1

        # Check if parameter validation is covered
        if any("parameter_validation" in case["name"] for case in test_cases):
            aspects_covered += 1

        # Check if performance is covered
        if any("performance" in case["name"] for case in test_cases):
            aspects_covered += 1

        # Check if integration is covered
        if any("integration" in case["name"] for case in test_cases):
            aspects_covered += 1

        aspect_coverage = aspects_covered / total_aspects

        # Combined coverage score
        coverage_score = (base_coverage + aspect_coverage) / 2.0

        return min(1.0, coverage_score)

    def _calculate_quality_score(
        self, validation_results: Dict[str, Any], coverage_score: float
    ) -> float:
        """Calculate quality score for generated test."""
        # Base quality from validation
        validation_score = (
            sum(
                [
                    1.0 if validation_results["syntax_valid"] else 0.0,
                    1.0 if validation_results["has_test_class"] else 0.0,
                    1.0 if validation_results["has_test_methods"] else 0.0,
                    1.0 if validation_results["has_assertions"] else 0.0,
                    1.0 if validation_results["has_mocking"] else 0.0,
                    1.0 if validation_results["has_documentation"] else 0.0,
                ]
            )
            / 6.0
        )

        # Coverage contribution
        coverage_contribution = coverage_score * 0.4

        # Final quality score
        quality_score = validation_score * 0.6 + coverage_contribution

        return quality_score

    def _generate_test_id(self, generated_logic: GeneratedLogic) -> str:
        """Generate unique test ID."""
        return f"test_{generated_logic.logic_id.lower()}"

    def _generate_test_name(self, generated_logic: GeneratedLogic) -> str:
        """Generate test name from logic."""
        logic_name = generated_logic.logic_name
        # Remove "Auto_" prefix if present
        if logic_name.startswith("Auto_"):
            logic_name = logic_name[5:]
        return f"Test{logic_name}"

    def get_generated_tests(
        self, logic_id: str = None, status: str = None
    ) -> List[GeneratedTest]:
        """Get generated tests, optionally filtered."""
        tests = list(self.generated_tests.values())

        if logic_id:
            tests = [test for test in tests if test.logic_id == logic_id]

        if status:
            tests = [test for test in tests if test.status == status]

        return tests

    def get_statistics(self) -> Dict[str, Any]:
        """Get test generation statistics."""
        total_generated = len(self.generated_tests)
        success_rate = (
            self.success_count / self.generation_count
            if self.generation_count > 0
            else 0.0
        )

        # Status distribution
        status_counts = {}
        for test in self.generated_tests.values():
            status_counts[test.status] = status_counts.get(test.status, 0) + 1

        # Coverage distribution
        coverage_scores = [
            test.coverage_score for test in self.generated_tests.values()
        ]
        avg_coverage = (
            sum(coverage_scores) / len(coverage_scores) if coverage_scores else 0.0
        )

        return {
            "total_generated": total_generated,
            "generation_count": self.generation_count,
            "success_count": self.success_count,
            "success_rate": success_rate,
            "average_coverage": avg_coverage,
            "status_distribution": status_counts,
        }


# Global instance for easy access
_test_generator = None


def get_test_generator() -> TestGenerator:
    """Get global test generator instance."""
    global _test_generator
    if _test_generator is None:
        _test_generator = TestGenerator()
    return _test_generator


def generate_test_for_logic(generated_logic: GeneratedLogic) -> GeneratedTest:
    """Convenience function to generate test for logic."""
    generator = get_test_generator()
    return generator.generate_test(generated_logic)


def get_test_generation_statistics() -> Dict[str, Any]:
    """Convenience function to get test generation statistics."""
    generator = get_test_generator()
    return generator.get_statistics()
