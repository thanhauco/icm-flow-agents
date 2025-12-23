"""Supervisor Agent: central orchestrator for the incident workflow."""

from __future__ import annotations

import asyncio
import json
import logging
import time

from ..config import prompts
from ..core.models import (
    IncidentResult,
    RawIncident,
    Severity,
    StructuredIncident,
    WorkflowPlan,
)
from .base import BaseAgent
from .impact_agent import ImpactAgent
from .mitigation_agent import MitigationAgent
from .noise_agent import NoiseAgent
from .summarizer import SummarizerAgent

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """Validates, plans, delegates, and aggregates the multi-agent workflow."""

    name = "supervisor"
    use_chat_model = True

    def __init__(
        self,
        llm=None,
        *,
        summarizer: SummarizerAgent | None = None,
        noise_agent: NoiseAgent | None = None,
        impact_agent: ImpactAgent | None = None,
        mitigation_agent: MitigationAgent | None = None,
    ) -> None:
        super().__init__(llm)
        self.summarizer = summarizer or SummarizerAgent(self.llm)
        self.noise_agent = noise_agent or NoiseAgent(self.llm)
        self.impact_agent = impact_agent or ImpactAgent(self.llm)
        self.mitigation_agent = mitigation_agent or MitigationAgent(self.llm)

    async def process_incident(
        self,
        incident: RawIncident | dict,
        *,
        similar_incidents: list[dict] | None = None,
    ) -> IncidentResult:
        """End-to-end processing of a single incident."""
        start = time.perf_counter()
        if isinstance(incident, dict):
            incident = RawIncident(**incident)

        errors: list[str] = []

        # 1. Summarize / normalize.
        structured = await self.summarizer.summarize(incident)

        # 2. Plan the workflow.
        plan = await self._plan(structured, similar_incidents or [])

        result = IncidentResult(incident=structured, plan=plan)

        # 3. Noise filtering (gate the rest of the pipeline).
        if plan.run_noise:
            noise = await self.noise_agent.evaluate(structured, similar_incidents)
            result.noise = noise
            if noise.is_noise:
                result.filtered_as_noise = True
                return self._finalize(result, start)

        # 4. Impact + mitigation can run; mitigation depends on impact.
        if plan.run_impact:
            result.impact = await self.impact_agent.assess(structured)

        if plan.run_mitigation:
            result.mitigation = await self.mitigation_agent.mitigate(
                structured, result.impact
            )

        return self._finalize(result, start, errors)

    async def process_batch(
        self, incidents: list[RawIncident | dict]
    ) -> list[IncidentResult]:
        """Process multiple incidents concurrently."""
        return await asyncio.gather(
            *(self.process_incident(inc) for inc in incidents)
        )

    async def _plan(
        self, incident: StructuredIncident, similar: list[dict]
    ) -> WorkflowPlan:
        user_prompt = prompts.SUPERVISOR_USER_PROMPT.format(
            incident_json=incident.model_dump_json(),
            similar_incidents=json.dumps(similar, default=str),
            system_state=json.dumps({"environment": "runtime"}),
        )
        response = await self._ask(prompts.SUPERVISOR_SYSTEM_PROMPT, user_prompt)
        data = response.json()
        try:
            priority = Severity(str(data.get("priority", incident.severity)).upper())
        except ValueError:
            priority = incident.severity
        return WorkflowPlan(
            run_noise=bool(data.get("run_noise", True)),
            run_impact=bool(data.get("run_impact", True)),
            run_mitigation=bool(data.get("run_mitigation", True)),
            priority=priority,
            reasoning=data.get("reasoning") or "",
        )

    def _finalize(
        self,
        result: IncidentResult,
        start: float,
        errors: list[str] | None = None,
    ) -> IncidentResult:
        result.errors = errors or []
        result.cost_usd = self._aggregate_cost()
        result.processing_ms = (time.perf_counter() - start) * 1000
        return result

    def _aggregate_cost(self) -> float:
        return (
            self.total_cost_usd
            + self.summarizer.total_cost_usd
            + self.noise_agent.total_cost_usd
            + self.impact_agent.total_cost_usd
            + self.mitigation_agent.total_cost_usd
        )
