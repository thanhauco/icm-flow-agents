"""Auto-Triage & Mitigation engine.

Acts on the outputs of the upstream agents (noise, impact, mitigation) to assign
an automated disposition and, when safe, execute low-risk runbook actions. Risky
or destructive actions are queued for human approval; high-severity incidents are
escalated to on-call. This is deterministic policy on top of the AI agents'
analysis — no additional model call is required.
"""

from __future__ import annotations

import logging

from ..config import get_settings
from ..core.models import (
    Escalation,
    ExecutedAction,
    IncidentResult,
    MitigationAction,
    Severity,
    TriageDecision,
    TriageDisposition,
)

logger = logging.getLogger(__name__)

#: Actions matching these verbs are safe to auto-execute when not flagged for approval.
_SAFE_VERBS = (
    "scale",
    "restart",
    "alert",
    "notify",
    "page",
    "circuit breaker",
    "reroute",
    "traffic",
    "failover",
    "increase",
    "flush cache",
    "clear cache",
    "throttle",
    "drain",
    "enable",
    "monitor",
)

#: Destructive verbs always require approval, even if the agent did not flag them.
_DESTRUCTIVE_VERBS = (
    "rollback",
    "deploy",
    "hotfix",
    "delete",
    "drop",
    "terminate",
    "wipe",
    "migrate",
    "patch",
    "restore",
    "reset",
    "revert",
)

_ESCALATE_SEVERITIES = {Severity.P0, Severity.P1}


def _is_safe(action: MitigationAction) -> bool:
    """Whether an action can be auto-executed without human approval."""
    text = action.action.lower()
    if action.requires_approval:
        return False
    if any(v in text for v in _DESTRUCTIVE_VERBS):
        return False
    return any(v in text for v in _SAFE_VERBS)


class AutoTriageEngine:
    """Assigns an automated disposition and runs safe mitigation actions."""

    def __init__(self) -> None:
        settings = get_settings()
        self._enabled = settings.auto_triage_enabled
        self._auto_mitigation = settings.auto_mitigation_enabled
        self._escalation_team = settings.auto_escalation_team

    @property
    def enabled(self) -> bool:
        return self._enabled

    def triage(self, result: IncidentResult) -> TriageDecision:
        """Produce a triage decision and auto-execute safe actions."""
        # Noise → auto-resolve, nothing to mitigate.
        if result.filtered_as_noise:
            score = result.noise.noise_score if result.noise else 100
            return TriageDecision(
                disposition=TriageDisposition.AUTO_RESOLVED,
                confidence=round(min(score, 100) / 100, 2),
                rationale="Classified as non-actionable noise; auto-closed.",
                auto_mitigation_enabled=self._auto_mitigation,
            )

        priority = self._priority(result)
        immediate = result.mitigation.immediate_actions if result.mitigation else []

        executed: list[ExecutedAction] = []
        pending: list[MitigationAction] = []
        for action in immediate:
            if self._auto_mitigation and _is_safe(action):
                executed.append(self._execute(action))
            else:
                pending.append(action)

        escalation: Escalation | None = None
        if priority in _ESCALATE_SEVERITIES:
            escalation = Escalation(
                team=self._escalation_team,
                reason=f"{priority.value} severity requires immediate on-call engagement.",
            )

        disposition = self._disposition(priority, executed, pending)
        confidence = self._confidence(result, priority)
        rationale = self._rationale(disposition, executed, pending, escalation)

        return TriageDecision(
            disposition=disposition,
            confidence=confidence,
            rationale=rationale,
            auto_executed=executed,
            pending_approval=pending,
            escalation=escalation,
            auto_mitigation_enabled=self._auto_mitigation,
        )

    def approve_pending(self, decision: TriageDecision) -> TriageDecision:
        """Execute all pending actions (human-approved) and update the decision."""
        for action in decision.pending_approval:
            decision.auto_executed.append(self._execute(action, status="executed (approved)"))
        decision.pending_approval = []
        if decision.disposition == TriageDisposition.AWAITING_APPROVAL:
            decision.disposition = TriageDisposition.AUTO_MITIGATED
            decision.rationale = "All pending actions approved and executed."
        return decision

    # -- internals ------------------------------------------------------
    @staticmethod
    def _execute(action: MitigationAction, status: str = "executed (simulated)") -> ExecutedAction:
        logger.info("Auto-triage executing action: %s", action.action)
        return ExecutedAction(action=action.action, status=status)

    @staticmethod
    def _priority(result: IncidentResult) -> Severity:
        if result.impact:
            return result.impact.priority
        if result.plan:
            return result.plan.priority
        return result.incident.severity

    @staticmethod
    def _disposition(
        priority: Severity,
        executed: list[ExecutedAction],
        pending: list[MitigationAction],
    ) -> TriageDisposition:
        if priority in _ESCALATE_SEVERITIES:
            return TriageDisposition.ESCALATED
        if pending:
            return TriageDisposition.AWAITING_APPROVAL
        if executed:
            return TriageDisposition.AUTO_MITIGATED
        return TriageDisposition.MONITOR

    @staticmethod
    def _confidence(result: IncidentResult, priority: Severity) -> float:
        if result.impact:
            return round(min(result.impact.impact_score, 100) / 100, 2)
        return 0.6 if priority in _ESCALATE_SEVERITIES else 0.5

    @staticmethod
    def _rationale(
        disposition: TriageDisposition,
        executed: list[ExecutedAction],
        pending: list[MitigationAction],
        escalation: Escalation | None,
    ) -> str:
        parts: list[str] = []
        if escalation:
            parts.append(f"Escalated to {escalation.team}.")
        if executed:
            parts.append(f"Auto-executed {len(executed)} safe action(s).")
        if pending:
            parts.append(f"{len(pending)} action(s) awaiting approval.")
        if not parts:
            parts.append("Low impact; monitoring without automated action.")
        return " ".join(parts)
