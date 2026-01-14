"""Tests for the Auto-Triage & Mitigation engine."""

import pytest

from src.agents.auto_triage import AutoTriageEngine, _is_safe
from src.core.models import (
    ImpactResult,
    IncidentResult,
    MitigationAction,
    MitigationResult,
    NoiseResult,
    Severity,
    StructuredIncident,
    TriageDisposition,
)


def _result(**kwargs) -> IncidentResult:
    incident = StructuredIncident(title="x", severity=kwargs.pop("severity", Severity.P3))
    return IncidentResult(incident=incident, **kwargs)


def test_is_safe_allows_scale_up():
    assert _is_safe(MitigationAction(action="Scale up affected service")) is True


def test_is_safe_blocks_destructive_even_if_not_flagged():
    assert _is_safe(MitigationAction(action="Rollback deployment", requires_approval=False)) is False


def test_is_safe_blocks_flagged_action():
    assert _is_safe(MitigationAction(action="Restart service", requires_approval=True)) is False


def test_noise_auto_resolved():
    engine = AutoTriageEngine()
    result = _result(filtered_as_noise=True, noise=NoiseResult(noise_score=90, is_noise=True))
    decision = engine.triage(result)
    assert decision.disposition == TriageDisposition.AUTO_RESOLVED
    assert not decision.auto_executed


def test_high_severity_escalates_and_auto_executes_safe():
    engine = AutoTriageEngine()
    result = _result(
        severity=Severity.P1,
        impact=ImpactResult(priority=Severity.P1, impact_score=80),
        mitigation=MitigationResult(
            immediate_actions=[
                MitigationAction(action="Scale up affected service"),
                MitigationAction(action="Apply hotfix", requires_approval=True),
            ]
        ),
    )
    decision = engine.triage(result)
    assert decision.disposition == TriageDisposition.ESCALATED
    assert decision.escalation is not None
    assert any("Scale up" in a.action for a in decision.auto_executed)
    assert any("hotfix" in a.action.lower() for a in decision.pending_approval)


def test_medium_severity_awaiting_approval_then_approved():
    engine = AutoTriageEngine()
    result = _result(
        severity=Severity.P3,
        impact=ImpactResult(priority=Severity.P3, impact_score=40),
        mitigation=MitigationResult(
            immediate_actions=[MitigationAction(action="Rollback deployment")]
        ),
    )
    decision = engine.triage(result)
    assert decision.disposition == TriageDisposition.AWAITING_APPROVAL
    assert decision.pending_approval

    approved = engine.approve_pending(decision)
    assert approved.disposition == TriageDisposition.AUTO_MITIGATED
    assert not approved.pending_approval
    assert approved.auto_executed


def test_no_actions_monitor():
    engine = AutoTriageEngine()
    result = _result(
        severity=Severity.P3,
        impact=ImpactResult(priority=Severity.P3, impact_score=20),
        mitigation=MitigationResult(immediate_actions=[]),
    )
    decision = engine.triage(result)
    assert decision.disposition == TriageDisposition.MONITOR
