"""Impact Agent (WF-10): assesses incident severity and customer impact."""

from __future__ import annotations

import json
import logging

from ..config import prompts
from ..core.models import ImpactResult, Severity, StructuredIncident
from .base import BaseAgent

logger = logging.getLogger(__name__)


class ImpactAgent(BaseAgent):
    """Produces a multi-dimensional impact assessment for an incident."""

    name = "impact"
    use_chat_model = False

    async def assess(
        self,
        incident: StructuredIncident,
        service_context: dict | None = None,
    ) -> ImpactResult:
        user_prompt = prompts.IMPACT_USER_PROMPT.format(
            incident_json=incident.model_dump_json(),
            service_context=json.dumps(service_context or {}, default=str),
        )
        response = await self._ask(prompts.IMPACT_SYSTEM_PROMPT, user_prompt)
        data = response.json()

        priority = data.get("priority")
        try:
            priority_enum = Severity(str(priority).upper()) if priority else incident.severity
        except ValueError:
            priority_enum = incident.severity

        return ImpactResult(
            priority=priority_enum,
            impact_score=int(data.get("impact_score") or 0),
            affected_users_estimate=int(data.get("affected_users_estimate") or 0),
            business_impact=data.get("business_impact") or "",
            sla_breach_risk=data.get("sla_breach_risk") or "low",
            reasoning=data.get("reasoning") or "",
        )
