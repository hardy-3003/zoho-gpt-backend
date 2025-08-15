"""
Logic Generation System for Auto-Expansion Capabilities

This module provides logic generation capabilities for creating
new logic modules based on detected patterns and requirements.
"""

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import hashlib

from helpers.history_store import write_event
from helpers.pattern_detector import RequestPattern

logger = logging.getLogger(__name__)


@dataclass
class GeneratedLogic:
    """Represents a generated logic module."""

    logic_id: str
    logic_name: str
    parameters: Dict[str, Any]
    generated_code: str
    validation_results: Dict[str, Any]
    complexity_score: float
    quality_score: float
    creation_date: datetime
    status: str  # 'draft', 'validated', 'active', 'deprecated'
    metadata: Dict[str, Any]


class LogicGenerator:
    """Logic generation system for auto-expansion capabilities."""

    def __init__(self, storage_path: str = "data/logic_generation/"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.generated_file = self.storage_path / "generated.json"
        self.generated_logics: Dict[str, GeneratedLogic] = {}
        self._load_data()

        self.quality_threshold = 0.7
        self.generation_count = 0
        self.success_count = 0

    def _load_data(self) -> None:
        """Load existing generation data."""
        try:
            if self.generated_file.exists():
                with open(self.generated_file, "r") as f:
                    data = json.load(f)
                    for logic_data in data.get("generated_logics", []):
                        logic = self._dict_to_generated_logic(logic_data)
                        self.generated_logics[logic.logic_id] = logic
            logger.info(f"Loaded {len(self.generated_logics)} generated logics")
        except Exception as e:
            logger.error(f"Error loading generation data: {e}")

    def _save_data(self) -> None:
        """Save generation data."""
        try:
            generated_data = {
                "generated_logics": [
                    asdict(logic) for logic in self.generated_logics.values()
                ],
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.generated_file, "w") as f:
                json.dump(generated_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving generation data: {e}")

    def _dict_to_generated_logic(self, data: Dict[str, Any]) -> GeneratedLogic:
        """Convert dictionary to GeneratedLogic."""
        return GeneratedLogic(
            logic_id=data["logic_id"],
            logic_name=data["logic_name"],
            parameters=data["parameters"],
            generated_code=data["generated_code"],
            validation_results=data["validation_results"],
            complexity_score=data["complexity_score"],
            quality_score=data["quality_score"],
            creation_date=datetime.fromisoformat(data["creation_date"]),
            status=data["status"],
            metadata=data["metadata"],
        )

    def generate_logic(
        self, pattern: RequestPattern, custom_parameters: Dict[str, Any] = None
    ) -> GeneratedLogic:
        """Generate a new logic based on pattern."""
        try:
            # Extract parameters
            parameters = self._extract_parameters(pattern, custom_parameters)

            # Generate code
            generated_code = self._generate_code(parameters, pattern)

            # Validate generated logic
            validation_results = self._validate_generated_logic(
                generated_code, parameters
            )

            # Calculate scores
            complexity_score = self._calculate_complexity_score(generated_code)
            quality_score = self._calculate_quality_score(
                validation_results, complexity_score
            )

            # Create generated logic
            logic_id = self._generate_logic_id(pattern)
            logic_name = self._generate_logic_name(pattern)

            generated_logic = GeneratedLogic(
                logic_id=logic_id,
                logic_name=logic_name,
                parameters=parameters,
                generated_code=generated_code,
                validation_results=validation_results,
                complexity_score=complexity_score,
                quality_score=quality_score,
                creation_date=datetime.now(),
                status=(
                    "draft" if quality_score < self.quality_threshold else "validated"
                ),
                metadata={
                    "pattern_id": pattern.pattern_id,
                    "generation_method": "pattern_based",
                },
            )

            # Store generated logic
            self.generated_logics[logic_id] = generated_logic

            # Update statistics
            self.generation_count += 1
            if quality_score >= self.quality_threshold:
                self.success_count += 1

            # Save data
            self._save_data()

            # Record event
            write_event(
                "logic_generated",
                {
                    "logic_id": logic_id,
                    "pattern_id": pattern.pattern_id,
                    "quality_score": quality_score,
                    "complexity_score": complexity_score,
                },
            )

            logger.info(
                f"Generated logic {logic_id} with quality score {quality_score:.2f}"
            )
            return generated_logic

        except Exception as e:
            logger.error(f"Failed to generate logic: {e}")
            raise

    def _extract_parameters(
        self, pattern: RequestPattern, custom_parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Extract parameters from pattern."""
        parameters = {}
        custom_params = custom_parameters or {}

        # Extract parameters from pattern query
        query_lower = pattern.query_text.lower()

        # Map common terms to parameters
        if "trend" in query_lower:
            parameters["analysis_type"] = "trend"
        elif "comparison" in query_lower:
            parameters["analysis_type"] = "comparison"
        elif "summary" in query_lower:
            parameters["analysis_type"] = "summary"
        else:
            parameters["analysis_type"] = "general"

        if "financial" in query_lower or "profit" in query_lower:
            parameters["data_source"] = "financial_data"
        else:
            parameters["data_source"] = "general_data"

        # Add custom parameters
        parameters.update(custom_params)

        return parameters

    def _generate_code(
        self, parameters: Dict[str, Any], pattern: RequestPattern
    ) -> str:
        """Generate code from parameters and pattern."""
        logic_id = self._generate_logic_id(pattern)
        logic_name = self._generate_logic_name(pattern)

        template_vars = {
            "logic_id": logic_id,
            "logic_name": logic_name,
            "description": f"Auto-generated logic for pattern: {pattern.query_text}",
            "tags": pattern.tags,
            "analysis_type": parameters.get("analysis_type", "general"),
            "data_source": parameters.get("data_source", "general_data"),
        }

        code_template = '''
"""
Title: {logic_name}
ID: {logic_id}
Tags: {tags}
Parent Logic: auto_generated
Required Inputs: Dict[str, Any]
Outputs: Dict[str, Any]
Assumptions: Data source is available and accessible
Evolution Notes: Auto-generated logic, may need refinement
"""

from typing import Any, Dict
from helpers.learning_hooks import record_feedback, score_confidence
from helpers.history_store import write_event
from helpers.rules_engine import validate_accounting
from logics.l4_contract_runtime import handle_l4

LOGIC_ID = "{logic_id}"
LOGIC_META = {{
    "id": "{logic_id}",
    "name": "{logic_name}",
    "description": "{description}",
    "tags": {tags},
    "category": "auto_generated",
    "complexity": "medium",
    "version": "1.0.0"
}}

def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle auto-generated logic request."""
    return handle_l4(payload, handle_logic, LOGIC_ID)

def handle_logic(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Main logic implementation."""
    try:
        # Extract parameters
        data_source = payload.get('data_source', '{data_source}')
        analysis_type = payload.get('analysis_type', '{analysis_type}')
        
        # Perform analysis
        result = _perform_analysis(data_source, analysis_type, payload)
        
        # Validate accounting rules
        validation_result = validate_accounting(result)
        
        # Record feedback
        record_feedback(LOGIC_ID, "success", {{
            "data_source": data_source,
            "analysis_type": analysis_type
        }})
        
        return {{
            "result": result,
            "provenance": {{
                "data_source": data_source,
                "analysis_type": analysis_type,
                "generated_from_pattern": True
            }},
            "confidence": score_confidence(result, validation_result),
            "alerts": validation_result.get("alerts", [])
        }}
        
    except Exception as e:
        record_feedback(LOGIC_ID, "error", {{"error": str(e)}})
        return {{
            "result": None,
            "provenance": {{}},
            "confidence": 0.0,
            "alerts": [f"Error in auto-generated logic: {{str(e)}}"]
        }}

def _perform_analysis(data_source: str, analysis_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Perform analysis based on type and data source."""
    return {{
        "analysis_type": analysis_type,
        "data_source": data_source,
        "analysis_data": {{}},
        "insights": [],
        "generated_at": "{{datetime.now().isoformat()}}"
    }}
'''

        return code_template.format(**template_vars)

    def _validate_generated_logic(
        self, code: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate generated logic code."""
        validation_results = {
            "syntax_valid": True,
            "has_required_functions": True,
            "has_proper_imports": True,
            "has_error_handling": True,
            "has_documentation": True,
            "alerts": [],
        }

        # Check syntax
        try:
            compile(code, "<generated>", "exec")
        except SyntaxError as e:
            validation_results["syntax_valid"] = False
            validation_results["alerts"].append(f"Syntax error: {e}")

        # Check for required functions
        if "def handle(" not in code:
            validation_results["has_required_functions"] = False
            validation_results["alerts"].append("Missing required 'handle' function")

        # Check for proper imports
        required_imports = [
            "helpers.learning_hooks",
            "helpers.history_store",
            "helpers.rules_engine",
        ]
        for imp in required_imports:
            if imp not in code:
                validation_results["has_proper_imports"] = False
                validation_results["alerts"].append(f"Missing import: {imp}")

        # Check for error handling
        if "try:" not in code or "except" not in code:
            validation_results["has_error_handling"] = False
            validation_results["alerts"].append("Missing error handling")

        # Check for documentation
        if '"""' not in code:
            validation_results["has_documentation"] = False
            validation_results["alerts"].append("Missing documentation")

        return validation_results

    def _calculate_complexity_score(self, code: str) -> float:
        """Calculate complexity score for generated code."""
        lines = code.split("\n")
        total_lines = len(lines)

        # Count complexity factors
        complexity_factors = 0

        # Function definitions
        function_count = code.count("def ")
        complexity_factors += function_count * 2

        # Conditional statements
        if_count = code.count("if ")
        complexity_factors += if_count

        # Loops
        loop_count = code.count("for ") + code.count("while ")
        complexity_factors += loop_count * 3

        # Exception handling
        try_count = code.count("try:")
        complexity_factors += try_count

        # Calculate complexity score
        complexity = min(1.0, (complexity_factors * 10) / total_lines)

        return complexity

    def _calculate_quality_score(
        self, validation_results: Dict[str, Any], complexity_score: float
    ) -> float:
        """Calculate quality score for generated logic."""
        # Base quality from validation
        validation_score = (
            sum(
                [
                    1.0 if validation_results["syntax_valid"] else 0.0,
                    1.0 if validation_results["has_required_functions"] else 0.0,
                    1.0 if validation_results["has_proper_imports"] else 0.0,
                    1.0 if validation_results["has_error_handling"] else 0.0,
                    1.0 if validation_results["has_documentation"] else 0.0,
                ]
            )
            / 5.0
        )

        # Complexity penalty
        complexity_penalty = max(0.0, complexity_score - 0.5) * 0.2

        # Final quality score
        quality_score = max(0.0, validation_score - complexity_penalty)

        return quality_score

    def _generate_logic_id(self, pattern: RequestPattern) -> str:
        """Generate unique logic ID."""
        # Find next available ID
        existing_ids = set()
        for logic in self.generated_logics.values():
            if logic.logic_id.startswith("L-"):
                try:
                    num = int(logic.logic_id[2:])
                    existing_ids.add(num)
                except ValueError:
                    pass

        next_id = 201  # Start after existing 200 logics
        while next_id in existing_ids:
            next_id += 1

        return f"L-{next_id:03d}"

    def _generate_logic_name(self, pattern: RequestPattern) -> str:
        """Generate logic name from pattern."""
        # Extract key terms from query
        words = pattern.query_text.split()

        # Remove common words
        common_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        key_words = [w for w in words if w not in common_words and len(w) > 3]

        if key_words:
            # Use first two key words
            name = "_".join(key_words[:2])
            return f"Auto_{name}_Logic"
        else:
            return f"Auto_Generated_Logic_{pattern.pattern_id[:8]}"

    def get_generated_logics(self, status: str = None) -> List[GeneratedLogic]:
        """Get generated logics, optionally filtered by status."""
        if status:
            return [
                logic
                for logic in self.generated_logics.values()
                if logic.status == status
            ]
        else:
            return list(self.generated_logics.values())

    def get_statistics(self) -> Dict[str, Any]:
        """Get generation statistics."""
        total_generated = len(self.generated_logics)
        success_rate = (
            self.success_count / self.generation_count
            if self.generation_count > 0
            else 0.0
        )

        # Status distribution
        status_counts = {}
        for logic in self.generated_logics.values():
            status_counts[logic.status] = status_counts.get(logic.status, 0) + 1

        return {
            "total_generated": total_generated,
            "generation_count": self.generation_count,
            "success_count": self.success_count,
            "success_rate": success_rate,
            "status_distribution": status_counts,
        }


# Global instance for easy access
_logic_generator = None


def get_logic_generator() -> LogicGenerator:
    """Get global logic generator instance."""
    global _logic_generator
    if _logic_generator is None:
        _logic_generator = LogicGenerator()
    return _logic_generator


def generate_logic_from_pattern(
    pattern: RequestPattern, custom_parameters: Dict[str, Any] = None
) -> GeneratedLogic:
    """Convenience function to generate logic from pattern."""
    generator = get_logic_generator()
    return generator.generate_logic(pattern, custom_parameters)


def get_generation_statistics() -> Dict[str, Any]:
    """Convenience function to get generation statistics."""
    generator = get_logic_generator()
    return generator.get_statistics()
