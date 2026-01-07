"""Aggregate runtime metrics across processed incidents.

Lightweight in-process counters that power the analytics panel in the web UI.
Reset whenever the process restarts; for durable analytics use the persisted
memory store or Application Insights.
"""

from __future__ import annotations

from ..core.models import IncidentResult
from ..output.evaluator import EvaluationReport


class MetricsTracker:
    """Accumulates counts and timings for processed incidents."""

    def __init__(self) -> None:
        self.incidents_total = 0
        self.noise_filtered = 0
        self.qa_passed = 0
        self.total_processing_ms = 0.0
        self.severity_counts: dict[str, int] = {}
        self.type_counts: dict[str, int] = {}
        self.disposition_counts: dict[str, int] = {}
        self.auto_actions_executed = 0
        self.escalations = 0

    def record(self, result: IncidentResult, report: EvaluationReport) -> None:
        self.incidents_total += 1
        self.total_processing_ms += result.processing_ms
        if result.filtered_as_noise:
            self.noise_filtered += 1
        if report.passed:
            self.qa_passed += 1

        sev = result.incident.severity.value
        self.severity_counts[sev] = self.severity_counts.get(sev, 0) + 1
        itype = result.incident.incident_type.value
        self.type_counts[itype] = self.type_counts.get(itype, 0) + 1

        if result.triage is not None:
            disp = result.triage.disposition.value
            self.disposition_counts[disp] = self.disposition_counts.get(disp, 0) + 1
            self.auto_actions_executed += len(result.triage.auto_executed)
            if result.triage.escalation is not None:
                self.escalations += 1

    def snapshot(self) -> dict:
        """Return computed aggregate metrics for serialization."""
        total = self.incidents_total or 1
        return {
            "incidents_total": self.incidents_total,
            "noise_filtered": self.noise_filtered,
            "noise_rate": round(self.noise_filtered / total, 4),
            "qa_pass_rate": round(self.qa_passed / total, 4),
            "avg_processing_ms": round(self.total_processing_ms / total, 2),
            "severity_counts": dict(self.severity_counts),
            "type_counts": dict(self.type_counts),
            "disposition_counts": dict(self.disposition_counts),
            "auto_actions_executed": self.auto_actions_executed,
            "escalations": self.escalations,
        }
