from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class ReconciliationResult:
    """Represents the result of a reconciliation check."""
    
    def __init__(self, is_valid: bool = True, score: float = 0.0, 
                 issues: List[str] = None, suggestions: List[str] = None,
                 corrections: Dict[str, Any] = None):
        self.is_valid = is_valid
        self.score = score
        self.issues = issues or []
        self.suggestions = suggestions or []
        self.corrections = corrections or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "score": self.score,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "corrections": self.corrections
        }


class ReconciliationEngine:
    """Engine for verifying totals, subtotals, and cross-field consistency."""
    
    def __init__(self, tolerance: float = 0.01):
        self.tolerance = tolerance
        self.verification_rules = self._load_verification_rules()
    
    def _load_verification_rules(self) -> Dict[str, Any]:
        """Load verification rules for different report types."""
        return {
            "pnl": {
                "total_formula": "revenue - expenses = net_profit",
                "required_fields": ["revenue", "expenses", "net_profit"],
                "subtotals": {
                    "gross_profit": "revenue - cost_of_goods_sold",
                    "operating_profit": "gross_profit - operating_expenses",
                    "net_profit": "operating_profit - other_expenses + other_income"
                },
                "consistency_checks": [
                    "revenue >= 0",
                    "expenses >= 0",
                    "net_profit can be negative"
                ]
            },
            "balance_sheet": {
                "total_formula": "assets = liabilities + equity",
                "required_fields": ["total_assets", "total_liabilities", "total_equity"],
                "subtotals": {
                    "current_assets": "cash + receivables + inventory + prepaid_expenses",
                    "fixed_assets": "property + equipment + intangible_assets",
                    "current_liabilities": "accounts_payable + short_term_debt + accrued_expenses",
                    "long_term_liabilities": "long_term_debt + deferred_tax"
                },
                "consistency_checks": [
                    "assets >= 0",
                    "liabilities >= 0",
                    "equity can be negative"
                ]
            },
            "cash_flow": {
                "total_formula": "operating_cash + investing_cash + financing_cash = net_cash_change",
                "required_fields": ["operating_cash", "investing_cash", "financing_cash", "net_cash_change"],
                "subtotals": {
                    "operating_cash": "net_income + depreciation + working_capital_changes",
                    "investing_cash": "capital_expenditures + asset_sales + investments",
                    "financing_cash": "debt_issuance + equity_issuance + dividends"
                }
            }
        }
    
    def verify_totals_and_subtotals(self, data: Dict[str, Any], 
                                  report_type: str = "auto") -> ReconciliationResult:
        """Verify totals and subtotals for a given report type."""
        result = ReconciliationResult()
        
        # Auto-detect report type if not specified
        if report_type == "auto":
            report_type = self._detect_report_type(data)
        
        if report_type not in self.verification_rules:
            result.issues.append(f"Unknown report type: {report_type}")
            return result
        
        rules = self.verification_rules[report_type]
        
        # Check required fields
        missing_fields = []
        for field in rules.get("required_fields", []):
            if field not in data:
                missing_fields.append(field)
        
        if missing_fields:
            result.issues.append(f"Missing required fields: {missing_fields}")
            result.score -= 0.3
        
        # Verify subtotals
        subtotal_issues = self._verify_subtotals(data, rules.get("subtotals", {}))
        result.issues.extend(subtotal_issues)
        
        # Verify main total formula
        total_issues = self._verify_total_formula(data, rules.get("total_formula", ""))
        result.issues.extend(total_issues)
        
        # Check consistency rules
        consistency_issues = self._check_consistency(data, rules.get("consistency_checks", []))
        result.issues.extend(consistency_issues)
        
        # Calculate score
        total_checks = len(rules.get("required_fields", [])) + len(rules.get("subtotals", {})) + 1
        failed_checks = len(result.issues)
        result.score = max(0.0, 1.0 - (failed_checks / total_checks))
        
        # Determine validity
        result.is_valid = result.score >= 0.7 and len(result.issues) <= 2
        
        # Generate suggestions
        result.suggestions = self._generate_suggestions(data, rules, result.issues)
        
        # Generate corrections
        result.corrections = self._generate_corrections(data, rules, result.issues)
        
        return result
    
    def _detect_report_type(self, data: Dict[str, Any]) -> str:
        """Auto-detect the report type based on field names."""
        field_names = [k.lower() for k in data.keys()]
        
        # P&L indicators
        pnl_indicators = ["revenue", "income", "expenses", "profit", "loss", "ebitda", "ebit"]
        pnl_score = sum(1 for indicator in pnl_indicators if any(indicator in field for field in field_names))
        
        # Balance Sheet indicators
        bs_indicators = ["assets", "liabilities", "equity", "capital", "debt", "cash"]
        bs_score = sum(1 for indicator in bs_indicators if any(indicator in field for field in field_names))
        
        # Cash Flow indicators
        cf_indicators = ["operating_cash", "investing_cash", "financing_cash", "cash_flow"]
        cf_score = sum(1 for indicator in cf_indicators if any(indicator in field for field in field_names))
        
        # Return the type with highest score
        scores = {"pnl": pnl_score, "balance_sheet": bs_score, "cash_flow": cf_score}
        return max(scores, key=scores.get)
    
    def _verify_subtotals(self, data: Dict[str, Any], subtotals: Dict[str, str]) -> List[str]:
        """Verify that subtotals match their component parts."""
        issues = []
        
        for subtotal_name, formula in subtotals.items():
            if subtotal_name not in data:
                continue
            
            # Parse formula (simple arithmetic for now)
            components = self._parse_formula(formula)
            if not components:
                continue
            
            # Calculate expected subtotal
            expected_value = 0.0
            missing_components = []
            
            for component in components:
                if component in data:
                    try:
                        expected_value += float(data[component])
                    except (ValueError, TypeError):
                        missing_components.append(component)
                else:
                    missing_components.append(component)
            
            if missing_components:
                issues.append(f"Missing components for {subtotal_name}: {missing_components}")
                continue
            
            # Compare with actual subtotal
            try:
                actual_value = float(data[subtotal_name])
                if abs(actual_value - expected_value) > self.tolerance:
                    issues.append(f"Subtotal mismatch for {subtotal_name}: expected {expected_value}, got {actual_value}")
            except (ValueError, TypeError):
                issues.append(f"Invalid subtotal value for {subtotal_name}: {data[subtotal_name]}")
        
        return issues
    
    def _verify_total_formula(self, data: Dict[str, Any], formula: str) -> List[str]:
        """Verify the main total formula."""
        issues = []
        
        if not formula:
            return issues
        
        # Parse formula (e.g., "assets = liabilities + equity")
        parts = formula.split("=")
        if len(parts) != 2:
            return issues
        
        left_side = parts[0].strip()
        right_side = parts[1].strip()
        
        # Calculate left side
        left_components = self._parse_formula(left_side)
        left_value = 0.0
        for component in left_components:
            if component in data:
                try:
                    left_value += float(data[component])
                except (ValueError, TypeError):
                    issues.append(f"Invalid value for {component}: {data[component]}")
                    return issues
            else:
                issues.append(f"Missing field for left side: {component}")
                return issues
        
        # Calculate right side
        right_components = self._parse_formula(right_side)
        right_value = 0.0
        for component in right_components:
            if component in data:
                try:
                    right_value += float(data[component])
                except (ValueError, TypeError):
                    issues.append(f"Invalid value for {component}: {data[component]}")
                    return issues
            else:
                issues.append(f"Missing field for right side: {component}")
                return issues
        
        # Compare sides
        if abs(left_value - right_value) > self.tolerance:
            issues.append(f"Total formula mismatch: {left_side} ({left_value}) != {right_side} ({right_value})")
        
        return issues
    
    def _parse_formula(self, formula: str) -> List[str]:
        """Parse a simple arithmetic formula into components."""
        # Remove spaces and split by operators
        formula = formula.replace(" ", "")
        components = re.split(r'[+\-*/]', formula)
        return [comp.strip() for comp in components if comp.strip()]
    
    def _check_consistency(self, data: Dict[str, Any], rules: List[str]) -> List[str]:
        """Check consistency rules."""
        issues = []
        
        for rule in rules:
            if ">=" in rule:
                # Parse "field >= 0" type rules
                parts = rule.split(">=")
                field = parts[0].strip()
                threshold = float(parts[1].strip())
                
                if field in data:
                    try:
                        value = float(data[field])
                        if value < threshold:
                            issues.append(f"Consistency violation: {field} ({value}) < {threshold}")
                    except (ValueError, TypeError):
                        issues.append(f"Invalid value for consistency check: {field} = {data[field]}")
        
        return issues
    
    def _generate_suggestions(self, data: Dict[str, Any], rules: Dict[str, Any], 
                            issues: List[str]) -> List[str]:
        """Generate suggestions for fixing issues."""
        suggestions = []
        
        for issue in issues:
            if "Missing required fields" in issue:
                suggestions.append("Add missing required fields to complete the report")
            elif "Subtotal mismatch" in issue:
                suggestions.append("Review component values and recalculate subtotals")
            elif "Total formula mismatch" in issue:
                suggestions.append("Check for data entry errors or missing transactions")
            elif "Consistency violation" in issue:
                suggestions.append("Review negative values and ensure they are intentional")
            elif "Invalid value" in issue:
                suggestions.append("Check data types and ensure numerical values are properly formatted")
        
        # General suggestions
        if len(issues) > 3:
            suggestions.append("Consider running a full data validation audit")
        
        if not suggestions:
            suggestions.append("Report appears to be consistent")
        
        return suggestions
    
    def _generate_corrections(self, data: Dict[str, Any], rules: Dict[str, Any], 
                            issues: List[str]) -> Dict[str, Any]:
        """Generate suggested corrections for issues."""
        corrections = {}
        
        for issue in issues:
            if "Subtotal mismatch" in issue:
                # Extract field name and expected value
                match = re.search(r'for (\w+): expected ([\d.]+), got ([\d.]+)', issue)
                if match:
                    field_name = match.group(1)
                    expected_value = float(match.group(2))
                    corrections[field_name] = expected_value
            
            elif "Total formula mismatch" in issue:
                # Suggest the correct total
                match = re.search(r'!= .*? \(([\d.]+)\)', issue)
                if match:
                    expected_total = float(match.group(1))
                    # Find which side needs correction (simplified)
                    corrections["suggested_total"] = expected_total
        
        return corrections


def reconcile_totals(data: Dict[str, Any], report_type: str = "auto", 
                    tolerance: float = 0.01) -> Dict[str, Any]:
    """Main function to reconcile totals and subtotals in report data.
    
    Args:
        data: Dictionary containing report data with field names as keys
        report_type: Type of report ("pnl", "balance_sheet", "cash_flow", or "auto")
        tolerance: Tolerance for numerical comparisons
        
    Returns:
        Dictionary with reconciliation results
    """
    engine = ReconciliationEngine(tolerance=tolerance)
    result = engine.verify_totals_and_subtotals(data, report_type)
    
    return {
        "reconciliation": result.to_dict(),
        "report_type": report_type,
        "data_summary": {
            "total_fields": len(data),
            "numerical_fields": sum(1 for v in data.values() if isinstance(v, (int, float))),
            "text_fields": sum(1 for v in data.values() if isinstance(v, str))
        }
    }


def cross_field_consistency_check(data: Dict[str, Any]) -> Dict[str, Any]:
    """Check for cross-field consistency issues."""
    issues = []
    suggestions = []
    
    # Check for duplicate field names with different values
    field_groups = {}
    for key, value in data.items():
        # Normalize field names (remove common prefixes/suffixes)
        normalized = re.sub(r'^(total_|net_|gross_)', '', key.lower())
        if normalized not in field_groups:
            field_groups[normalized] = []
        field_groups[normalized].append((key, value))
    
    for normalized, fields in field_groups.items():
        if len(fields) > 1:
            # Check if values are different
            values = [f[1] for f in fields]
            if len(set(values)) > 1:
                issues.append(f"Conflicting values for similar fields: {[f[0] for f in fields]}")
                suggestions.append(f"Review and standardize field naming for {normalized}")
    
    # Check for logical inconsistencies
    if "revenue" in data and "expenses" in data and "net_profit" in data:
        try:
            revenue = float(data["revenue"])
            expenses = float(data["expenses"])
            net_profit = float(data["net_profit"])
            
            expected_profit = revenue - expenses
            if abs(net_profit - expected_profit) > 0.01:
                issues.append(f"Net profit ({net_profit}) doesn't match revenue ({revenue}) - expenses ({expenses})")
                suggestions.append("Recalculate net profit or review revenue/expense values")
        except (ValueError, TypeError):
            pass
    
    # Check for negative values where they shouldn't be
    for key, value in data.items():
        if isinstance(value, (int, float)) and value < 0:
            if any(term in key.lower() for term in ["revenue", "income", "assets"]):
                issues.append(f"Negative value for {key}: {value}")
                suggestions.append(f"Review if negative {key} is intentional")
    
    return {
        "is_consistent": len(issues) == 0,
        "issues": issues,
        "suggestions": suggestions,
        "field_count": len(data),
        "conflict_count": len(issues)
    }


def detect_mismatches(extracted_data: Dict[str, Any], 
                     generated_data: Dict[str, Any],
                     tolerance: float = 0.01) -> Dict[str, Any]:
    """Detect mismatches between extracted and generated data."""
    mismatches = []
    corrections = {}
    
    # Compare common fields
    common_fields = set(extracted_data.keys()) & set(generated_data.keys())
    
    for field in common_fields:
        extracted_value = extracted_data[field]
        generated_value = generated_data[field]
        
        try:
            # Try numerical comparison
            extracted_num = float(extracted_value)
            generated_num = float(generated_value)
            
            if abs(extracted_num - generated_num) > tolerance:
                mismatches.append({
                    "field": field,
                    "extracted": extracted_value,
                    "generated": generated_value,
                    "difference": abs(extracted_num - generated_num),
                    "type": "numerical"
                })
                corrections[field] = extracted_value  # Prefer extracted value
        except (ValueError, TypeError):
            # String comparison
            if str(extracted_value) != str(generated_value):
                mismatches.append({
                    "field": field,
                    "extracted": extracted_value,
                    "generated": generated_value,
                    "difference": "string_mismatch",
                    "type": "text"
                })
                corrections[field] = extracted_value
    
    # Check for missing fields
    missing_in_generated = set(extracted_data.keys()) - set(generated_data.keys())
    missing_in_extracted = set(generated_data.keys()) - set(extracted_data.keys())
    
    for field in missing_in_generated:
        mismatches.append({
            "field": field,
            "extracted": extracted_data[field],
            "generated": "MISSING",
            "difference": "missing_in_generated",
            "type": "missing"
        })
        corrections[field] = extracted_data[field]
    
    for field in missing_in_extracted:
        mismatches.append({
            "field": field,
            "extracted": "MISSING",
            "generated": generated_data[field],
            "difference": "missing_in_extracted",
            "type": "missing"
        })
    
    return {
        "mismatches": mismatches,
        "corrections": corrections,
        "summary": {
            "total_mismatches": len(mismatches),
            "numerical_mismatches": len([m for m in mismatches if m["type"] == "numerical"]),
            "text_mismatches": len([m for m in mismatches if m["type"] == "text"]),
            "missing_fields": len([m for m in mismatches if m["type"] == "missing"]),
            "fields_compared": len(common_fields),
            "missing_in_generated": len(missing_in_generated),
            "missing_in_extracted": len(missing_in_extracted)
        }
    }


def generate_correction_suggestions(mismatches: List[Dict[str, Any]]) -> List[str]:
    """Generate human-readable correction suggestions."""
    suggestions = []
    
    numerical_mismatches = [m for m in mismatches if m["type"] == "numerical"]
    text_mismatches = [m for m in mismatches if m["type"] == "text"]
    missing_fields = [m for m in mismatches if m["type"] == "missing"]
    
    if numerical_mismatches:
        suggestions.append(f"Found {len(numerical_mismatches)} numerical mismatches - review calculations")
    
    if text_mismatches:
        suggestions.append(f"Found {len(text_mismatches)} text mismatches - check field mappings")
    
    if missing_fields:
        suggestions.append(f"Found {len(missing_fields)} missing fields - ensure complete data extraction")
    
    # Specific suggestions for common issues
    for mismatch in mismatches[:5]:  # Limit to first 5 for readability
        field = mismatch["field"]
        if "revenue" in field.lower() or "income" in field.lower():
            suggestions.append(f"Review {field} calculation - may need tax adjustments")
        elif "expense" in field.lower() or "cost" in field.lower():
            suggestions.append(f"Check {field} categorization and allocation")
        elif "profit" in field.lower() or "loss" in field.lower():
            suggestions.append(f"Verify {field} calculation against revenue and expenses")
    
    if not suggestions:
        suggestions.append("No corrections needed - data appears consistent")
    
    return suggestions
