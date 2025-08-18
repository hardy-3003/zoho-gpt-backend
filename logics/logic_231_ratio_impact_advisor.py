"""
Title: Ratio Impact Advisor
ID: L-231
Tags: ["ratios", "bank", "advisory", "behavior"]
Category: Dynamic(Behavior)
Required Inputs: {"org_id": "string", "period": "YYYY-MM", "proposed_entry": {...}}
Outputs: {"impact_report": {...}, "suggestions": [...]}
Assumptions: Covenants in /configs/bank_covenants.yaml; deterministic ratio functions in /helpers/ratios.py
Evidence: trial_balance, journal_entries (simulated), bank_covenant_config
Evolution Notes: Learns from accept/reject decisions per org/facility.
"""

import hashlib
import json
from typing import Any

import yaml
from evidence.ledger import attach_evidence

from helpers import ratios
from helpers.cache import cache_get, cache_set
from helpers.history_store import write_event
from helpers.learning_hooks import record_feedback, score_confidence
from helpers.rules_engine import validate_accounting
from helpers.schema_registry import validate_payload


def load_covenants(org_id: str) -> dict[str, Any]:
    """Load covenant configuration for the organization."""
    try:
        with open("configs/bank_covenants.yaml") as f:
            cfg = yaml.safe_load(f)

        # Return org-specific config or default
        return cfg.get(org_id, cfg.get("default", {}))
    except FileNotFoundError:
        # Fallback to default values if config file not found
        return {
            "thresholds": {
                "dscr": 1.50,
                "icr": 3.00,
                "current_ratio": 1.25,
                "quick_ratio": 1.00,
                "de_ratio": 1.00,
            },
            "buffer_percentage": 0.10,
            "policy": {"block_on_breach": False},
        }


def load_ratio_targets(org_id: str) -> dict[str, Any]:
    """Load ratio targets configuration for the organization."""
    try:
        with open("configs/ratio_targets.yaml") as f:
            cfg = yaml.safe_load(f)

        # Return org-specific config or default
        return cfg.get(org_id, cfg.get("default", {}))
    except FileNotFoundError:
        # Fallback to default values if config file not found
        return {
            "targets": {
                "dscr": 2.00,
                "icr": 4.00,
                "current_ratio": 1.50,
                "quick_ratio": 1.25,
                "de_ratio": 0.75,
            }
        }


def simulate_tb_with_entry(tb: dict[str, Any], je: dict[str, Any]) -> dict[str, Any]:
    """Apply DR/CR lines to a cloned TB deterministically."""
    clone = json.loads(json.dumps(tb))

    for line in je.get("lines", []):
        account = line.get("account", "")
        dr_amount = float(line.get("dr", 0.0))
        cr_amount = float(line.get("cr", 0.0))

        if account in clone:
            clone[account]["dr"] = clone[account].get("dr", 0.0) + dr_amount
            clone[account]["cr"] = clone[account].get("cr", 0.0) + cr_amount
        else:
            clone[account] = {"dr": dr_amount, "cr": cr_amount}

    return clone


def generate_evidence_hash(
    tb: dict[str, Any], je: dict[str, Any], covenants: dict[str, Any]
) -> str:
    """Generate deterministic hash for evidence."""
    # Create a stable representation for hashing
    data = {
        "tb": dict(sorted(tb.items())),
        "je": dict(sorted(je.items())),
        "covenants": dict(sorted(covenants.items())),
    }

    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle ratio impact analysis for proposed journal entries."""
    validate_payload("L-231", payload)

    org_id = payload["org_id"]
    period = payload["period"]
    je = payload["proposed_entry"]

    # Generate cache key based on inputs
    cache_key = ("L-231", org_id, period, generate_evidence_hash({}, je, {}))

    # Check cache first
    if cached := cache_get(cache_key):
        return cached

    # Load configurations
    covenants = load_covenants(org_id)
    # targets = load_ratio_targets(org_id)  # TODO: Use targets for internal benchmarking

    # Fetch trial balance
    tb_before = ratios.fetch_trial_balance(org_id, period)

    # Compute baseline ratios
    before_ratios = ratios.compute_all(tb_before)

    # Simulate post-entry trial balance
    tb_after = simulate_tb_with_entry(tb_before, je)
    after_ratios = ratios.compute_all(tb_after)

    # Calculate deltas
    deltas = {}
    for ratio_name in before_ratios:
        if ratio_name in after_ratios:
            deltas[ratio_name] = round(
                after_ratios[ratio_name] - before_ratios[ratio_name], 6
            )

    # Check for breaches
    breaches = []
    alerts = []

    for ratio_name, threshold in covenants.get("thresholds", {}).items():
        if ratio_name in after_ratios:
            current_value = after_ratios[ratio_name]

            # Check if ratio is breached
            if ratio_name in ["dscr", "icr", "current_ratio", "quick_ratio"]:
                if current_value < threshold:
                    breaches.append(
                        {
                            "ratio": ratio_name,
                            "threshold": threshold,
                            "after": current_value,
                            "facility": covenants.get("facility_id", "DEFAULT"),
                        }
                    )
                    alerts.append(
                        {
                            "code": f"RATIO_{ratio_name.upper()}_BREACH",
                            "severity": "error",
                            "message": f"{ratio_name.upper()} below threshold {threshold} after JE",
                            "evidence": [],
                        }
                    )
            elif ratio_name in ["de_ratio"]:
                if current_value > threshold:
                    breaches.append(
                        {
                            "ratio": ratio_name,
                            "threshold": threshold,
                            "after": current_value,
                            "facility": covenants.get("facility_id", "DEFAULT"),
                        }
                    )
                    alerts.append(
                        {
                            "code": f"RATIO_{ratio_name.upper()}_BREACH",
                            "severity": "error",
                            "message": f"{ratio_name.upper()} above threshold {threshold} after JE",
                            "evidence": [],
                        }
                    )

    # Generate suggestions if breaches or near-breaches
    suggestions = []
    if breaches or ratios.is_near_breach(after_ratios, covenants):
        suggestions = ratios.generate_suggestions(je, tb_before, covenants)

    # Create impact report
    impact_report = {
        "before": before_ratios,
        "after": after_ratios,
        "deltas": deltas,
        "breaches": breaches,
    }

    # Generate evidence
    evidence_hash = generate_evidence_hash(tb_before, je, covenants)
    provenance = attach_evidence(
        {"impact_report": impact_report, "je": je, "covenants": covenants},
        sources={
            "tb_before": tb_before,
            "tb_after": tb_after,
            "evidence_hash": evidence_hash,
        },
    )

    # Create output
    out = {
        "result": {"impact_report": impact_report, "suggestions": suggestions},
        "provenance": provenance,
        "confidence": score_confidence(impact_report, alerts=alerts),
        "alerts": alerts,
        "applied_rule_set": {"packs": {}, "effective_date_window": None},
    }

    # Validate accounting
    validate_accounting(out["result"])

    # Record event and feedback
    write_event(
        logic="L-231", inputs=payload, outputs=out["result"], provenance=provenance
    )
    record_feedback("L-231", context=payload, outputs=out["result"])

    # Cache result
    cache_set(cache_key, out, ttl_seconds=3600)

    return out
