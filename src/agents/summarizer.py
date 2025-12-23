"""Summarizer Agent: normalizes raw incidents into structured records."""

from __future__ import annotations

import json
import logging

from ..config import prompts
from ..core.models import IncidentType, RawIncident, Severity, StructuredIncident
from .base import BaseAgent

logger = logging.getLogger(__name__)


class SummarizerAgent(BaseAgent):
    """Transforms raw incident text into a ``StructuredIncident``."""

    name = "summarizer"
    use_chat_model = False

    async def summarize(self, raw: RawIncident) -> StructuredIncident:
        user_prompt = prompts.SUMMARIZER_USER_PROMPT.format(
            raw_content=raw.content,
            metadata=json.dumps(raw.metadata, default=str),
        )
        response = await self._ask(prompts.SUMMARIZER_SYSTEM_PROMPT, user_prompt)
        data = response.json()

        return StructuredIncident(
            title=data.get("title") or "Untitled incident",
            description=data.get("description") or raw.content[:500],
            incident_type=_safe_enum(IncidentType, data.get("incident_type"), IncidentType.UNKNOWN),
            category=data.get("category") or "general",
            severity=_safe_enum(Severity, data.get("severity"), Severity.P3),
            affected_services=list(data.get("affected_services") or []),
            error_patterns=list(data.get("error_patterns") or []),
            keywords=list(data.get("keywords") or []),
            confidence=float(data.get("confidence") or 0.0),
            source=raw.source,
            timestamp=raw.timestamp,
            metadata=raw.metadata,
        )


def _safe_enum(enum_cls, value, default):
    """Coerce a string into an enum member, falling back to ``default``."""
    if value is None:
        return default
    try:
        return enum_cls(str(value).lower() if enum_cls is IncidentType else str(value).upper())
    except ValueError:
        return default
