"""
Canonical Contract Dataclasses for Zoho GPT Backend

This module defines the authoritative dataclasses for all public surfaces
and orchestrator plan items. These contracts serve as cross-phase anchors
and are enforced via schema hash snapshots.

Task P1.2.1 — Contract dataclasses & schema hash snapshots
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum


class LogicCategory(Enum):
    """Logic module categories as defined in MASTER_SCOPE_OF_WORK.md"""

    STATIC = "Static"
    DYNAMIC_REGULATION = "Dynamic(Regulation)"
    DYNAMIC_PATTERNS = "Dynamic(Patterns)"
    DYNAMIC_GROWTH = "Dynamic(Growth)"
    DYNAMIC_BEHAVIOR = "Dynamic(Behavior)"


class AlertSeverity(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class Alert:
    """Standard alert structure for all logic outputs"""

    code: str
    severity: AlertSeverity
    message: str
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AppliedRuleSet:
    """Applied rule packs and effective date window"""

    packs: Dict[str, str] = field(default_factory=dict)
    effective_date_window: Optional[Dict[str, str]] = None


@dataclass
class LogicOutput:
    """Standard output contract for all logic modules"""

    result: Union[Dict[str, Any], List[Any], Any]
    provenance: Dict[str, List[str]] = field(default_factory=dict)
    confidence: float = 0.0
    alerts: List[Alert] = field(default_factory=list)
    applied_rule_set: AppliedRuleSet = field(default_factory=AppliedRuleSet)
    explanation: Optional[str] = None


@dataclass
class LogicMetadata:
    """Metadata for logic module registration"""

    title: str
    logic_id: str
    tags: List[str] = field(default_factory=list)
    category: LogicCategory = LogicCategory.STATIC
    required_inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    evidence_sources: List[str] = field(default_factory=list)
    evolution_notes: List[str] = field(default_factory=list)


@dataclass
class ExecuteRequest:
    """Request contract for /api/execute endpoint"""

    logic_id: str
    org_id: str
    period: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecuteResponse:
    """Response contract for /api/execute endpoint"""

    logic_output: LogicOutput
    execution_time_ms: float
    cache_hit: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorPlanItem:
    """Individual item in an orchestrator execution plan"""

    logic_id: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    timeout_seconds: Optional[int] = None
    retry_config: Optional[Dict[str, Any]] = None


@dataclass
class OrchestratorPlan:
    """Complete orchestrator execution plan"""

    plan_id: str
    items: List[OrchestratorPlanItem] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OrchestratorOutput:
    """Standard output contract for orchestrators"""

    sections: Dict[str, LogicOutput] = field(default_factory=dict)
    alerts: List[Alert] = field(default_factory=list)
    completeness: float = 0.0
    applied_rule_set: AppliedRuleSet = field(default_factory=AppliedRuleSet)
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPSearchRequest:
    """Request contract for /mcp/search endpoint"""

    query: str
    org_id: str
    period: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPSearchResponse:
    """Response contract for /mcp/search endpoint"""

    plan: OrchestratorPlan
    confidence: float = 0.0
    explanation: Optional[str] = None


@dataclass
class MCPFetchRequest:
    """Request contract for /mcp/fetch endpoint"""

    plan: OrchestratorPlan
    stream: bool = False
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPFetchResponse:
    """Response contract for /mcp/fetch endpoint"""

    result: OrchestratorOutput
    stream_events: Optional[List[Dict[str, Any]]] = None


@dataclass
class SSEEvent:
    """Server-Sent Event structure for streaming responses"""

    event_type: str
    data: Dict[str, Any]
    event_id: Optional[str] = None
    retry: Optional[int] = None


@dataclass
class WebhookPayload:
    """Standard webhook payload structure"""

    event_type: str
    org_id: str
    timestamp: datetime
    payload: Dict[str, Any] = field(default_factory=dict)
    signature: Optional[str] = None


@dataclass
class CLICommand:
    """CLI command structure"""

    command: str
    subcommand: Optional[str] = None
    arguments: List[str] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CLIResponse:
    """CLI response structure"""

    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


# Evidence and Regulatory OS Contracts


@dataclass
class EvidenceNode:
    """Evidence node in the WORM ledger"""

    id: str
    hash: str
    source: str
    meta: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RulePack:
    """Regulatory rule pack structure"""

    pack_id: str
    effective_from: str
    effective_to: Optional[str] = None
    rules: List[Dict[str, Any]] = field(default_factory=list)
    fixtures: Dict[str, str] = field(default_factory=dict)
    tests: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ConsentObject:
    """Consent object for data access"""

    subject: str
    purpose: str
    expires_at: datetime
    retention_days: int
    scope: List[str] = field(default_factory=list)
    lawful_basis: Optional[str] = None


# Ratio Impact Advisor Specific Contracts (L-231)


@dataclass
class JournalEntryLine:
    """Individual line in a journal entry"""

    account: str
    dr: float = 0.0
    cr: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JournalEntry:
    """Complete journal entry structure"""

    date: str
    lines: List[JournalEntryLine] = field(default_factory=list)
    notes: str = ""
    source: str = "ui"


@dataclass
class RatioImpactRequest:
    """Request for ratio impact analysis"""

    org_id: str
    period: str
    proposed_entry: JournalEntry
    facility_ids: List[str] = field(default_factory=list)


@dataclass
class RatioBreach:
    """Ratio breach detection result"""

    ratio: str
    threshold: float
    after: float
    facility: Optional[str] = None


@dataclass
class RatioSuggestion:
    """Advisory suggestion for ratio improvement"""

    title: str
    rationale: str
    compliance_refs: List[str] = field(default_factory=list)
    projected_after: Dict[str, float] = field(default_factory=dict)
    posting_patch: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RatioImpactReport:
    """Complete ratio impact analysis"""

    before: Dict[str, float] = field(default_factory=dict)
    after: Dict[str, float] = field(default_factory=dict)
    deltas: Dict[str, float] = field(default_factory=dict)
    breaches: List[RatioBreach] = field(default_factory=list)


@dataclass
class RatioImpactOutput:
    """Output for ratio impact advisor logic"""

    impact_report: RatioImpactReport
    suggestions: List[RatioSuggestion] = field(default_factory=list)


# Contract validation helpers


def validate_contract_structure(obj: Any, expected_type: type) -> bool:
    """Validate that an object matches the expected contract structure"""
    if not isinstance(obj, expected_type):
        return False

    # For dataclasses, check all required fields are present
    if hasattr(obj, "__dataclass_fields__"):
        for field_name, field_info in obj.__dataclass_fields__.items():
            if (
                not field_info.init
                or field_info.default is not field_info.default_factory
            ):
                if not hasattr(obj, field_name):
                    return False

    return True


def get_contract_hash(contract_class: type) -> str:
    """Generate a deterministic hash for a contract class structure"""
    import hashlib
    import inspect

    # Get the source code of the class
    source = inspect.getsource(contract_class)

    # Create a hash of the source
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


# Export all contracts for use in other modules
__all__ = [
    "LogicCategory",
    "AlertSeverity",
    "Alert",
    "AppliedRuleSet",
    "LogicOutput",
    "LogicMetadata",
    "ExecuteRequest",
    "ExecuteResponse",
    "OrchestratorPlanItem",
    "OrchestratorPlan",
    "OrchestratorOutput",
    "MCPSearchRequest",
    "MCPSearchResponse",
    "MCPFetchRequest",
    "MCPFetchResponse",
    "SSEEvent",
    "WebhookPayload",
    "CLICommand",
    "CLIResponse",
    "EvidenceNode",
    "RulePack",
    "ConsentObject",
    "JournalEntryLine",
    "JournalEntry",
    "RatioImpactRequest",
    "RatioBreach",
    "RatioSuggestion",
    "RatioImpactReport",
    "RatioImpactOutput",
    "validate_contract_structure",
    "get_contract_hash",
]
