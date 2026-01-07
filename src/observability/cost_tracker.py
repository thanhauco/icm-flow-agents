"""Cost tracking and budget enforcement per incident."""

from __future__ import annotations

import logging

from ..config import get_settings

logger = logging.getLogger(__name__)


class CostTracker:
    """Accumulates LLM spend and flags budget breaches."""

    def __init__(self) -> None:
        self._total_usd = 0.0
        self._per_incident: dict[str, float] = {}
        self._budget = get_settings().max_cost_per_incident_usd

    def add(self, incident_id: str, cost_usd: float) -> None:
        self._total_usd += cost_usd
        self._per_incident[incident_id] = (
            self._per_incident.get(incident_id, 0.0) + cost_usd
        )
        if self._per_incident[incident_id] > self._budget:
            logger.warning(
                "Incident %s exceeded budget: $%.4f > $%.4f",
                incident_id,
                self._per_incident[incident_id],
                self._budget,
            )

    @property
    def total_usd(self) -> float:
        return self._total_usd

    def for_incident(self, incident_id: str) -> float:
        return self._per_incident.get(incident_id, 0.0)

    def over_budget(self, incident_id: str) -> bool:
        return self.for_incident(incident_id) > self._budget

# Optimizations for token usage metrics tracking
