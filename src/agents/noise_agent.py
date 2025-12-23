"""Noise Agent (WF-5): filters false positives and non-actionable alerts."""

from __future__ import annotations

import json
import logging

from ..config import get_settings, prompts
from ..core.models import NoiseResult, StructuredIncident
from .base import BaseAgent

logger = logging.getLogger(__name__)


class NoiseAgent(BaseAgent):
    """Scores an incident's likelihood of being noise."""

    name = "noise"
    use_chat_model = False

    def __init__(self, llm=None) -> None:
        super().__init__(llm)
        self._threshold = get_settings().noise_filter_threshold

    async def evaluate(
        self,
        incident: StructuredIncident,
        similar_incidents: list[dict] | None = None,
    ) -> NoiseResult:
        user_prompt = prompts.NOISE_USER_PROMPT.format(
            incident_json=incident.model_dump_json(),
            similar_incidents=json.dumps(similar_incidents or [], default=str),
        )
        response = await self._ask(prompts.NOISE_SYSTEM_PROMPT, user_prompt)
        data = response.json()

        score = int(data.get("noise_score") or 0)
        # Trust the model's boolean if present, else apply the configured threshold.
        is_noise = bool(data.get("is_noise")) if "is_noise" in data else score >= self._threshold
        return NoiseResult(
            noise_score=score,
            is_noise=is_noise,
            patterns_detected=list(data.get("patterns_detected") or []),
            reasoning=data.get("reasoning") or "",
        )
