"""LLM client wrapper around Azure OpenAI with a local fallback.

When Azure OpenAI credentials are configured the real ``AsyncAzureOpenAI``
client is used. Otherwise a deterministic offline stub is returned so the
system remains runnable for local development and tests without secrets.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..config import get_settings
from .azure_credentials import get_azure_credential

logger = logging.getLogger(__name__)

# Rough Azure OpenAI pricing (USD per 1K tokens) used for cost estimation.
_COST_PER_1K_PROMPT = 0.005
_COST_PER_1K_COMPLETION = 0.015


class LLMResponse:
    """Container for an LLM completion plus usage metadata."""

    def __init__(self, content: str, prompt_tokens: int = 0, completion_tokens: int = 0):
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens

    @property
    def cost_usd(self) -> float:
        return (
            self.prompt_tokens / 1000 * _COST_PER_1K_PROMPT
            + self.completion_tokens / 1000 * _COST_PER_1K_COMPLETION
        )

    def json(self) -> dict[str, Any]:
        """Parse the completion as JSON, tolerating markdown code fences."""
        text = self.content.strip()
        if text.startswith("```"):
            # Strip ```json ... ``` fences.
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip("` \n")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("LLM response was not valid JSON: %s", text[:200])
            return {}


class LLMClient:
    """Async wrapper providing a single ``complete`` method to all agents."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: Any | None = None
        self._live = self._settings.has_azure_openai
        if self._live:
            try:
                from azure.identity import get_bearer_token_provider
                from openai import AsyncAzureOpenAI

                kwargs: dict[str, Any] = {
                    "azure_endpoint": self._settings.azure_openai_endpoint,
                    "api_version": self._settings.azure_openai_api_version,
                }
                if self._settings.azure_openai_api_key:
                    kwargs["api_key"] = self._settings.azure_openai_api_key
                else:
                    kwargs["azure_ad_token_provider"] = get_bearer_token_provider(
                        get_azure_credential(),
                        "https://cognitiveservices.azure.com/.default",
                    )

                self._client = AsyncAzureOpenAI(**kwargs)
            except Exception as exc:  # pragma: no cover - import/config guard
                logger.warning("Falling back to offline LLM stub: %s", exc)
                self._live = False

    @property
    def is_live(self) -> bool:
        return self._live

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        use_chat_model: bool = False,
        json_mode: bool = True,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Run a chat completion. Returns a deterministic stub when offline."""
        if not self._live or self._client is None:
            return _offline_completion(system_prompt, user_prompt)

        deployment = (
            self._settings.azure_openai_chat_deployment_name
            if use_chat_model
            else self._settings.azure_openai_deployment_name
        )
        kwargs: dict[str, Any] = {
            "model": deployment,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "timeout": self._settings.request_timeout_seconds,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        resp = await self._client.chat.completions.create(**kwargs)
        usage = resp.usage
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
        )


def _offline_completion(system_prompt: str, user_prompt: str) -> LLMResponse:
    """Heuristic offline responder.

    Inspects the system prompt to decide which agent is calling and returns a
    plausible JSON payload derived from simple keyword rules over the user
    prompt. This keeps the full pipeline exercisable without Azure access.
    """
    text = user_prompt.lower()

    def has(*words: str) -> bool:
        return any(w in text for w in words)

    if "summarizer" in system_prompt.lower() or "normalized, structured" in system_prompt:
        if has("down", "outage", "unavailable"):
            itype, sev = "outage", "P1"
        elif has("slow", "latency", "timeout"):
            itype, sev = "degradation", "P2"
        elif has("breach", "attack", "unauthorized"):
            itype, sev = "security", "P0"
        elif has("error", "exception", "failed"):
            itype, sev = "error", "P2"
        else:
            itype, sev = "unknown", "P3"
        payload = {
            "title": "Auto-summarized incident",
            "description": user_prompt[:280],
            "incident_type": itype,
            "category": "infrastructure",
            "severity": sev,
            "affected_services": [],
            "error_patterns": [],
            "keywords": [w for w in ("database", "network", "api", "timeout") if w in text],
            "confidence": 0.6,
        }
    elif "supervisor agent" in system_prompt.lower():
        payload = {
            "run_noise": True,
            "run_impact": True,
            "run_mitigation": not has("test", "ignore"),
            "priority": "P1" if has("p0", "p1", "outage", "critical") else "P3",
            "reasoning": "Offline heuristic plan.",
        }
    elif "noise agent" in system_prompt.lower():
        is_noise = has("test", "flapping", "duplicate", "ignore")
        payload = {
            "noise_score": 85 if is_noise else 20,
            "is_noise": is_noise,
            "patterns_detected": ["test_alert"] if is_noise else [],
            "reasoning": "Offline heuristic noise scoring.",
        }
    elif "impact agent" in system_prompt.lower():
        high = has("outage", "critical", "p0", "p1", "all services")
        payload = {
            "priority": "P1" if high else "P3",
            "impact_score": 80 if high else 35,
            "affected_users_estimate": 15000 if high else 200,
            "business_impact": "Revenue impact likely." if high else "Limited.",
            "sla_breach_risk": "high" if high else "low",
            "reasoning": "Offline heuristic impact scoring.",
        }
    elif "mitigation agent" in system_prompt.lower():
        payload = {
            "root_causes": [{"hypothesis": "Resource exhaustion", "probability": 0.5}],
            "immediate_actions": [
                {"action": "Scale up affected service", "requires_approval": False},
                {"action": "Alert on-call team", "requires_approval": False},
            ],
            "short_term_actions": [
                {"action": "Apply hotfix", "requires_approval": True}
            ],
            "long_term_actions": [
                {"action": "Add capacity monitoring", "requires_approval": False}
            ],
            "reasoning": "Offline heuristic mitigation plan.",
        }
    else:
        payload = {}

    content = json.dumps(payload)
    # Approximate token usage for cost tracking parity with live mode.
    prompt_tokens = max(1, len(system_prompt + user_prompt) // 4)
    completion_tokens = max(1, len(content) // 4)
    return LLMResponse(content, prompt_tokens, completion_tokens)

# Enhanced retry logic with exponential backoff and error classification
