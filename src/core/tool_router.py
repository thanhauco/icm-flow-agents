"""Tool router: rule-based routing hints derived from a structured incident."""

from __future__ import annotations

import logging

from .models import IncidentType, Severity, StructuredIncident

logger = logging.getLogger(__name__)

_HIGH_SEVERITY = {Severity.P0, Severity.P1}


class ToolRouter:
    """Produces lightweight routing hints to bias supervisor planning.

    The supervisor makes the authoritative decision, but these heuristics give
    a fast, deterministic baseline and are useful when the LLM is unavailable.
    """

    def route(self, incident: StructuredIncident) -> dict[str, bool]:
        keywords = " ".join(incident.keywords + [incident.title]).lower()

        noise_candidate = any(
            k in keywords for k in ("test", "flapping", "duplicate")
        )
        high_severity = incident.severity in _HIGH_SEVERITY
        needs_mitigation = incident.incident_type in {
            IncidentType.OUTAGE,
            IncidentType.DEGRADATION,
            IncidentType.SECURITY,
        }

        hints = {
            "run_noise": True,
            "run_impact": high_severity or not noise_candidate,
            "run_mitigation": needs_mitigation,
        }
        logger.debug("Routing hints for %s: %s", incident.incident_id, hints)
        return hints
