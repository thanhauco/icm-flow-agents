"""Shared domain models for the ICM Flow Agents system.

These Pydantic models define the contract passed between the input layer,
the agents, and the output layer. They mirror the schemas described in
``docs/AGENT_SPECIFICATIONS.md``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_incident_id() -> str:
    return f"INC-{_utcnow():%Y}-{uuid.uuid4().hex[:8]}"


class Severity(str, Enum):
    """Incident priority levels (P0 most severe, P4 informational)."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class IncidentType(str, Enum):
    OUTAGE = "outage"
    DEGRADATION = "degradation"
    SECURITY = "security"
    ERROR = "error"
    WARNING = "warning"
    UNKNOWN = "unknown"


class RawIncident(BaseModel):
    """Unprocessed incident as ingested from a source channel."""

    source: str = Field(description="Origin channel: email, chat, logs, api.")
    content: str = Field(description="Raw, unstructured incident text.")
    timestamp: datetime = Field(default_factory=_utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructuredIncident(BaseModel):
    """Normalized incident produced by the Summarizer Agent."""

    incident_id: str = Field(default_factory=_new_incident_id)
    title: str = ""
    description: str = ""
    incident_type: IncidentType = IncidentType.UNKNOWN
    category: str = "general"
    severity: Severity = Severity.P3
    affected_services: list[str] = Field(default_factory=list)
    error_patterns: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    source: str = "unknown"
    timestamp: datetime = Field(default_factory=_utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NoiseResult(BaseModel):
    """Output of the Noise Agent (WF-5)."""

    noise_score: int = 0
    is_noise: bool = False
    patterns_detected: list[str] = Field(default_factory=list)
    reasoning: str = ""


class ImpactResult(BaseModel):
    """Output of the Impact Agent (WF-10)."""

    priority: Severity = Severity.P3
    impact_score: int = 0
    affected_users_estimate: int = 0
    business_impact: str = ""
    sla_breach_risk: str = "low"
    reasoning: str = ""


class MitigationAction(BaseModel):
    action: str
    requires_approval: bool = False


class RootCause(BaseModel):
    hypothesis: str
    probability: float = 0.0


class MitigationResult(BaseModel):
    """Output of the Mitigation Agent (WF-25)."""

    root_causes: list[RootCause] = Field(default_factory=list)
    immediate_actions: list[MitigationAction] = Field(default_factory=list)
    short_term_actions: list[MitigationAction] = Field(default_factory=list)
    long_term_actions: list[MitigationAction] = Field(default_factory=list)
    reasoning: str = ""


class WorkflowPlan(BaseModel):
    """Supervisor's delegation decision for an incident."""

    run_noise: bool = True
    run_impact: bool = True
    run_mitigation: bool = True
    priority: Severity = Severity.P3
    reasoning: str = ""


class TriageDisposition(str, Enum):
    """Automated disposition assigned by the Auto-Triage engine."""

    AUTO_RESOLVED = "auto_resolved"
    AUTO_MITIGATED = "auto_mitigated"
    AWAITING_APPROVAL = "awaiting_approval"
    ESCALATED = "escalated"
    MONITOR = "monitor"


class ExecutedAction(BaseModel):
    """A mitigation action the engine executed (or simulated)."""

    action: str
    status: str = "executed"
    category: str = "remediation"
    executed_at: datetime = Field(default_factory=_utcnow)


class Escalation(BaseModel):
    team: str
    reason: str


class TriageDecision(BaseModel):
    """Output of the Auto-Triage & Mitigation engine."""

    disposition: TriageDisposition = TriageDisposition.MONITOR
    confidence: float = 0.0
    rationale: str = ""
    auto_executed: list[ExecutedAction] = Field(default_factory=list)
    pending_approval: list[MitigationAction] = Field(default_factory=list)
    escalation: Escalation | None = None
    auto_mitigation_enabled: bool = True


class IncidentResult(BaseModel):
    """Aggregated end-to-end result for a single incident."""

    incident: StructuredIncident
    plan: WorkflowPlan | None = None
    noise: NoiseResult | None = None
    impact: ImpactResult | None = None
    mitigation: MitigationResult | None = None
    triage: TriageDecision | None = None
    filtered_as_noise: bool = False
    errors: list[str] = Field(default_factory=list)
    cost_usd: float = 0.0
    processing_ms: float = 0.0
    completed_at: datetime = Field(default_factory=_utcnow)
