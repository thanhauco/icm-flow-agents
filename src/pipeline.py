"""High-level pipeline wiring the full incident-management flow together."""

from __future__ import annotations

import logging
from typing import Any

from .agents import AutoTriageEngine, SupervisorAgent
from .core import LLMClient, MemoryManager, VectorStore
from .core.models import IncidentResult, TriageDecision
from .input import DataIngestion
from .observability import CostTracker, ErrorHandler, MetricsTracker
from .output import EvaluationReport, Evaluator

logger = logging.getLogger(__name__)


class IncidentPipeline:
    """Orchestrates ingestion → supervision → triage → evaluation for incidents."""

    def __init__(
        self,
        *,
        llm: LLMClient | None = None,
        memory: MemoryManager | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.llm = llm or LLMClient()
        self.memory = memory or MemoryManager()
        self.ingestion = DataIngestion()
        self.supervisor = SupervisorAgent(self.llm)
        self.vector_store = vector_store or VectorStore()
        self.evaluator = Evaluator()
        self.cost_tracker = CostTracker()
        self.error_handler = ErrorHandler()
        self.auto_triage = AutoTriageEngine()
        self.metrics = MetricsTracker()
        #: Triage decisions kept in memory so pending actions can be approved later.
        self._triage_store: dict[str, TriageDecision] = {}

    async def run(self, payload: dict[str, Any]) -> tuple[IncidentResult, EvaluationReport]:
        """Process a single incident payload end-to-end."""
        incident, warnings = self.ingestion.ingest(payload)
        if warnings:
            logger.info("Governance warnings: %s", warnings)

        # Retrieve historical context for the planner and noise agent.
        similar = self.vector_store.search(incident.content, top_k=3)

        try:
            result = await self.supervisor.process_incident(
                incident, similar_incidents=similar
            )
        except Exception as exc:  # noqa: BLE001 - top-level safety net
            self.error_handler.record("pipeline", exc)
            raise

        result.errors.extend(warnings)
        self.cost_tracker.add(result.incident.incident_id, result.cost_usd)

        # Auto-triage: assign a disposition and run safe mitigation actions.
        if self.auto_triage.enabled:
            result.triage = self.auto_triage.triage(result)
            self._triage_store[result.incident.incident_id] = result.triage

        report = self.evaluator.evaluate(result)
        self.metrics.record(result, report)
        self.memory.persist(
            result.incident.incident_id,
            {
                "incident": result.incident.model_dump(mode="json"),
                "filtered_as_noise": result.filtered_as_noise,
                "impact": result.impact.model_dump(mode="json") if result.impact else None,
                "mitigation": result.mitigation.model_dump(mode="json")
                if result.mitigation
                else None,
                "triage": result.triage.model_dump(mode="json") if result.triage else None,
                "evaluation": {
                    "passed": report.passed,
                    "score": report.score,
                    "issues": report.issues,
                },
            },
        )

        # Index the processed incident so future incidents can find it.
        self.vector_store.index(
            result.incident.incident_id,
            f"{result.incident.title} {result.incident.description}",
            metadata={"severity": result.incident.severity.value},
        )

        return result, report

    def approve_pending(self, incident_id: str) -> TriageDecision | None:
        """Execute the pending (human-approved) actions for an incident."""
        decision = self._triage_store.get(incident_id)
        if decision is None:
            return None
        updated = self.auto_triage.approve_pending(decision)
        self._triage_store[incident_id] = updated
        return updated

    async def run_batch(
        self, payloads: list[dict[str, Any]]
    ) -> list[tuple[IncidentResult, EvaluationReport]]:
        results = []
        for payload in payloads:
            results.append(await self.run(payload))
        return results
