"""Base class shared by all specialized agents."""

from __future__ import annotations

import logging

from ..core.llm_client import LLMClient, LLMResponse

logger = logging.getLogger(__name__)


class BaseAgent:
    """Common LLM plumbing and cost accounting for agents."""

    name: str = "base"
    #: Whether this agent should use the interactive chat model.
    use_chat_model: bool = False

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()
        self.total_cost_usd: float = 0.0

    async def _ask(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.2
    ) -> LLMResponse:
        """Call the LLM, accumulate cost, and return the response."""
        logger.debug("[%s] invoking LLM (live=%s)", self.name, self.llm.is_live)
        response = await self.llm.complete(
            system_prompt,
            user_prompt,
            use_chat_model=self.use_chat_model,
            temperature=temperature,
        )
        self.total_cost_usd += response.cost_usd
        return response
