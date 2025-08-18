#!/usr/bin/env python3
"""
Dashboard Renderer/Validator Tool

Validates dashboard JSON schemas and prints summary of panels and queries.
"""

import argparse
import json
import sys
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

# Dashboard schema validation
DASHBOARD_SCHEMA = {
    "type": "object",
    "required": ["dashboard"],
    "properties": {
        "dashboard": {
            "type": "object",
            "required": ["title", "panels"],
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "version": {"type": "string"},
                "refresh_interval": {"type": "string"},
                "time_range": {"type": "string"},
                "panels": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "title", "type"],
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "type": {"type": "string"},
                            "position": {"type": "object"},
                            "targets": {"type": "array"},
                            "options": {"type": "object"},
                            "thresholds": {"type": "array"},
                            "y_axis": {"type": "object"},
                            "transformations": {"type": "array"},
                            "columns": {"type": "array"},
                        },
                    },
                },
                "templating": {"type": "object"},
                "annotations": {"type": "object"},
                "links": {"type": "array"},
            },
        }
    },
}


def validate_dashboard_schema(dashboard_data: Dict[str, Any]) -> List[str]:
    """Validate dashboard against schema and return list of errors."""
    errors = []

    # Basic structure validation
    if "dashboard" not in dashboard_data:
        errors.append("Missing 'dashboard' root key")
        return errors

    dashboard = dashboard_data["dashboard"]

    # Required fields
    required_fields = ["title", "panels"]
    for field in required_fields:
        if field not in dashboard:
            errors.append(f"Missing required field: {field}")

    # Validate panels
    if "panels" in dashboard:
        panels = dashboard["panels"]
        if not isinstance(panels, list):
            errors.append("'panels' must be an array")
        else:
            for i, panel in enumerate(panels):
                panel_errors = validate_panel(panel, i)
                errors.extend(panel_errors)

    # Validate templating
    if "templating" in dashboard:
        templating_errors = validate_templating(dashboard["templating"])
        errors.extend(templating_errors)

    # Validate links
    if "links" in dashboard:
        links_errors = validate_links(dashboard["links"])
        errors.extend(links_errors)

    return errors


def validate_panel(panel: Dict[str, Any], index: int) -> List[str]:
    """Validate a single panel and return list of errors."""
    errors = []

    # Required fields
    required_fields = ["id", "title", "type"]
    for field in required_fields:
        if field not in panel:
            errors.append(f"Panel {index}: Missing required field: {field}")

    # Validate panel ID format
    if "id" in panel:
        panel_id = panel["id"]
        if not isinstance(panel_id, str) or not panel_id.strip():
            errors.append(f"Panel {index}: Invalid panel ID: {panel_id}")

    # Validate panel type
    valid_types = [
        "stat",
        "timeseries",
        "table",
        "piechart",
        "gauge",
        "heatmap",
        "graph",
    ]
    if "type" in panel:
        panel_type = panel["type"]
        if panel_type not in valid_types:
            errors.append(f"Panel {index}: Invalid panel type: {panel_type}")

    # Validate targets
    if "targets" in panel:
        targets = panel["targets"]
        if not isinstance(targets, list):
            errors.append(f"Panel {index}: 'targets' must be an array")
        else:
            for j, target in enumerate(targets):
                target_errors = validate_target(target, index, j)
                errors.extend(target_errors)

    # Validate position
    if "position" in panel:
        position_errors = validate_position(panel["position"], index)
        errors.extend(position_errors)

    return errors


def validate_target(
    target: Dict[str, Any], panel_index: int, target_index: int
) -> List[str]:
    """Validate a single target and return list of errors."""
    errors = []

    # Required fields
    required_fields = ["query"]
    for field in required_fields:
        if field not in target:
            errors.append(
                f"Panel {panel_index}, Target {target_index}: Missing required field: {field}"
            )

    # Validate query format
    if "query" in target:
        query = target["query"]
        if not isinstance(query, str) or not query.strip():
            errors.append(
                f"Panel {panel_index}, Target {target_index}: Invalid query: {query}"
            )

    # Validate format
    if "format" in target:
        valid_formats = ["number", "percent", "ms", "short", "heatmap", "graph"]
        format_val = target["format"]
        if format_val not in valid_formats:
            errors.append(
                f"Panel {panel_index}, Target {target_index}: Invalid format: {format_val}"
            )

    return errors


def validate_position(position: Dict[str, Any], panel_index: int) -> List[str]:
    """Validate panel position and return list of errors."""
    errors = []

    required_fields = ["x", "y", "w", "h"]
    for field in required_fields:
        if field not in position:
            errors.append(f"Panel {panel_index}: Missing position field: {field}")
        elif not isinstance(position[field], int):
            errors.append(
                f"Panel {panel_index}: Position field {field} must be integer"
            )

    return errors


def validate_templating(templating: Dict[str, Any]) -> List[str]:
    """Validate templating configuration and return list of errors."""
    errors = []

    if "list" in templating:
        templating_list = templating["list"]
        if not isinstance(templating_list, list):
            errors.append("'templating.list' must be an array")
        else:
            for i, item in enumerate(templating_list):
                if not isinstance(item, dict):
                    errors.append(f"Templating item {i}: Must be an object")
                else:
                    if "name" not in item:
                        errors.append(f"Templating item {i}: Missing 'name' field")
                    if "type" not in item:
                        errors.append(f"Templating item {i}: Missing 'type' field")

    return errors


def validate_links(links: List[Dict[str, Any]]) -> List[str]:
    """Validate dashboard links and return list of errors."""
    errors = []

    for i, link in enumerate(links):
        if not isinstance(link, dict):
            errors.append(f"Link {i}: Must be an object")
        else:
            if "title" not in link:
                errors.append(f"Link {i}: Missing 'title' field")
            if "url" not in link:
                errors.append(f"Link {i}: Missing 'url' field")

    return errors


def analyze_dashboard(dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze dashboard and return summary information."""
    dashboard = dashboard_data.get("dashboard", {})

    analysis = {
        "title": dashboard.get("title", "Unknown"),
        "description": dashboard.get("description", ""),
        "version": dashboard.get("version", "1.0"),
        "refresh_interval": dashboard.get("refresh_interval", "30s"),
        "time_range": dashboard.get("time_range", "1h"),
        "total_panels": 0,
        "panel_types": {},
        "queries": set(),
        "templating_variables": 0,
        "links": 0,
        "annotations": 0,
    }

    # Analyze panels
    panels = dashboard.get("panels", [])
    analysis["total_panels"] = len(panels)

    for panel in panels:
        panel_type = panel.get("type", "unknown")
        analysis["panel_types"][panel_type] = (
            analysis["panel_types"].get(panel_type, 0) + 1
        )

        # Collect queries
        targets = panel.get("targets", [])
        for target in targets:
            query = target.get("query", "")
            if query:
                analysis["queries"].add(query)

    # Analyze templating
    templating = dashboard.get("templating", {})
    templating_list = templating.get("list", [])
    analysis["templating_variables"] = len(templating_list)

    # Analyze links
    links = dashboard.get("links", [])
    analysis["links"] = len(links)

    # Analyze annotations
    annotations = dashboard.get("annotations", {})
    annotations_list = annotations.get("list", [])
    analysis["annotations"] = len(annotations_list)

    # Convert queries set to list for JSON serialization
    analysis["queries"] = list(analysis["queries"])

    return analysis


def print_dashboard_summary(analysis: Dict[str, Any], filename: str):
    """Print a summary of the dashboard analysis."""
    print(f"\n📊 Dashboard: {analysis['title']}")
    print(f"📁 File: {filename}")
    print(f"📝 Description: {analysis['description']}")
    print(f"🔢 Version: {analysis['version']}")
    print(f"🔄 Refresh: {analysis['refresh_interval']}")
    print(f"⏰ Time Range: {analysis['time_range']}")
    print()

    print(f"📈 Panels: {analysis['total_panels']}")
    if analysis["panel_types"]:
        print("   Panel Types:")
        for panel_type, count in analysis["panel_types"].items():
            print(f"     - {panel_type}: {count}")

    print(f"🔍 Queries: {len(analysis['queries'])}")
    if analysis["queries"]:
        print("   Sample Queries:")
        for query in sorted(analysis["queries"])[:5]:  # Show first 5
            print(f"     - {query}")
        if len(analysis["queries"]) > 5:
            print(f"     ... and {len(analysis['queries']) - 5} more")

    print(f"⚙️  Templating Variables: {analysis['templating_variables']}")
    print(f"🔗 Links: {analysis['links']}")
    print(f"📌 Annotations: {analysis['annotations']}")


def validate_dashboard_file(filepath: str, verbose: bool = False) -> bool:
    """Validate a single dashboard file and return success status."""
    try:
        with open(filepath, "r") as f:
            dashboard_data = json.load(f)

        # Validate schema
        errors = validate_dashboard_schema(dashboard_data)

        if errors:
            print(f"❌ {filepath}: Validation failed")
            for error in errors:
                print(f"   - {error}")
            return False

        # Analyze dashboard
        analysis = analyze_dashboard(dashboard_data)

        if verbose:
            print_dashboard_summary(analysis, filepath)
        else:
            print(f"✅ {filepath}: Valid dashboard")

        return True

    except json.JSONDecodeError as e:
        print(f"❌ {filepath}: Invalid JSON - {e}")
        return False
    except Exception as e:
        print(f"❌ {filepath}: Error - {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Dashboard Renderer/Validator Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a single dashboard
  python tools/render_dashboards.py dashboards/orchestrators.json

  # Validate all dashboards with verbose output
  python tools/render_dashboards.py --validate dashboards/*.json --verbose

  # Generate summary report
  python tools/render_dashboards.py --summary dashboards/*.json
        """,
    )

    parser.add_argument("files", nargs="+", help="Dashboard JSON files to process")

    parser.add_argument(
        "--validate", action="store_true", help="Validate dashboard schemas"
    )

    parser.add_argument(
        "--summary", action="store_true", help="Generate summary report"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    parser.add_argument(
        "--output", "-o", help="Output file for summary (default: stdout)"
    )

    args = parser.parse_args()

    # Default to validation if no specific action
    if not args.validate and not args.summary:
        args.validate = True

    valid_count = 0
    total_count = 0
    all_analyses = []

    for filepath in args.files:
        if not os.path.exists(filepath):
            print(f"❌ {filepath}: File not found")
            continue

        total_count += 1

        try:
            with open(filepath, "r") as f:
                dashboard_data = json.load(f)

            # Validate if requested
            if args.validate:
                errors = validate_dashboard_schema(dashboard_data)
                if errors:
                    print(f"❌ {filepath}: Validation failed")
                    for error in errors:
                        print(f"   - {error}")
                    continue
                else:
                    print(f"✅ {filepath}: Valid dashboard")
                    valid_count += 1

            # Analyze if requested
            if args.summary or args.verbose:
                analysis = analyze_dashboard(dashboard_data)
                all_analyses.append((filepath, analysis))

                if args.verbose:
                    print_dashboard_summary(analysis, filepath)

        except json.JSONDecodeError as e:
            print(f"❌ {filepath}: Invalid JSON - {e}")
        except Exception as e:
            print(f"❌ {filepath}: Error - {e}")

    # Print summary
    if args.summary and all_analyses:
        print("\n" + "=" * 60)
        print("📊 DASHBOARD SUMMARY REPORT")
        print("=" * 60)

        # Overall statistics
        total_panels = sum(a[1]["total_panels"] for a in all_analyses)
        total_queries = len(set().union(*[set(a[1]["queries"]) for a in all_analyses]))

        print(f"📁 Total Dashboards: {len(all_analyses)}")
        print(f"📈 Total Panels: {total_panels}")
        print(f"🔍 Total Unique Queries: {total_queries}")
        print()

        # Dashboard list
        print("📋 Dashboard List:")
        for filepath, analysis in all_analyses:
            print(f"   - {analysis['title']} ({filepath})")
            print(
                f"     Panels: {analysis['total_panels']}, Queries: {len(analysis['queries'])}"
            )

        # Panel type distribution
        all_panel_types = {}
        for _, analysis in all_analyses:
            for panel_type, count in analysis["panel_types"].items():
                all_panel_types[panel_type] = all_panel_types.get(panel_type, 0) + count

        if all_panel_types:
            print("\n📊 Panel Type Distribution:")
            for panel_type, count in sorted(all_panel_types.items()):
                print(f"   - {panel_type}: {count}")

        # Query analysis
        all_queries = set().union(*[set(a[1]["queries"]) for a in all_analyses])
        if all_queries:
            print(f"\n🔍 Query Analysis:")
            print(f"   Total Unique Queries: {len(all_queries)}")

            # Group queries by prefix
            query_groups = {}
            for query in all_queries:
                prefix = query.split("_")[0] if "_" in query else query
                query_groups[prefix] = query_groups.get(prefix, 0) + 1

            print("   Query Groups:")
            for prefix, count in sorted(query_groups.items()):
                print(f"     - {prefix}*: {count} queries")

    # Print validation summary
    if args.validate:
        print(f"\n📊 Validation Summary: {valid_count}/{total_count} dashboards valid")
        if valid_count == total_count:
            print("✅ All dashboards are valid!")
        else:
            print(f"❌ {total_count - valid_count} dashboards have issues")

    # Exit with appropriate code
    if args.validate and valid_count != total_count:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
