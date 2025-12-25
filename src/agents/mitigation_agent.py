"""Mitigation Agent (WF-25): generates time-phased remediation plans."""

from __future__ import annotations

import json
import logging

from ..config import prompts
from ..core.models import (
    ImpactResult,
    MitigationAction,
    MitigationResult,
    RootCause,
    StructuredIncident,
)
from .base import BaseAgent

logger = logging.getLogger(__name__)


class MitigationAgent(BaseAgent):
    """Performs root-cause analysis and builds an actionable mitigation plan."""

    name = "mitigation"
    use_chat_model = False

    async def mitigate(
        self,
        incident: StructuredIncident,
        impact: ImpactResult | None = None,
        playbooks: list[dict] | None = None,
    ) -> MitigationResult:
        user_prompt = prompts.MITIGATION_USER_PROMPT.format(
            incident_json=incident.model_dump_json(),
            impact_json=impact.model_dump_json() if impact else "{}",
            playbooks=json.dumps(playbooks or [], default=str),
        )
        response = await self._ask(prompts.MITIGATION_SYSTEM_PROMPT, user_prompt)
        data = response.json()

        return MitigationResult(
            root_causes=[
                RootCause(
                    hypothesis=rc.get("hypothesis", ""),
                    probability=float(rc.get("probability") or 0.0),
                )
                for rc in (data.get("root_causes") or [])
            ],
            immediate_actions=_actions(data.get("immediate_actions")),
            short_term_actions=_actions(data.get("short_term_actions")),
            long_term_actions=_actions(data.get("long_term_actions")),
            reasoning=data.get("reasoning") or "",
        )


def _actions(raw: list | None) -> list[MitigationAction]:
    return [
        MitigationAction(
            action=item.get("action", ""),
            requires_approval=bool(item.get("requires_approval")),
        )
        for item in (raw or [])
        if item.get("action")
    ]
