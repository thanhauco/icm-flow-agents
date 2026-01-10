"""Formatters for presenting incident results."""

from __future__ import annotations

from ..core.models import IncidentResult


def to_summary_dict(result: IncidentResult) -> dict:
    """Compact, serializable summary of an incident result."""
    return {
        "incident_id": result.incident.incident_id,
        "title": result.incident.title,
        "type": result.incident.incident_type.value,
        "severity": result.incident.severity.value,
        "filtered_as_noise": result.filtered_as_noise,
        "priority": result.plan.priority.value if result.plan else None,
        "impact_score": result.impact.impact_score if result.impact else None,
        "immediate_actions": (
            [a.action for a in result.mitigation.immediate_actions]
            if result.mitigation
            else []
        ),
        "cost_usd": round(result.cost_usd, 6),
        "processing_ms": round(result.processing_ms, 2),
        "errors": result.errors,
    }


def format_result(result: IncidentResult) -> str:
    """Human-readable multi-line report for an incident result."""
    inc = result.incident
    lines = [
        f"Incident {inc.incident_id}: {inc.title}",
        f"  Type: {inc.incident_type.value} | Severity: {inc.severity.value}",
    ]
    if result.filtered_as_noise and result.noise:
        lines.append(
            f"  FILTERED AS NOISE (score={result.noise.noise_score}): {result.noise.reasoning}"
        )
        return "\n".join(lines)

    if result.impact:
        lines.append(
            f"  Impact: priority={result.impact.priority.value}, "
            f"score={result.impact.impact_score}, "
            f"~users={result.impact.affected_users_estimate}, "
            f"SLA risk={result.impact.sla_breach_risk}"
        )
    if result.mitigation:
        lines.append("  Mitigation - Immediate:")
        for action in result.mitigation.immediate_actions:
            flag = " [APPROVAL REQUIRED]" if action.requires_approval else ""
            lines.append(f"    - {action.action}{flag}")
    lines.append(
        f"  Cost: ${result.cost_usd:.4f} | Time: {result.processing_ms:.0f} ms"
    )
    if result.errors:
        lines.append(f"  Errors: {'; '.join(result.errors)}")
    return "\n".join(lines)
