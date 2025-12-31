"""Data ingestion pipeline: validate, sanitize, and normalize raw input."""

from __future__ import annotations

import logging
from typing import Any

from ..core.models import RawIncident
from ..governance import AIGovernance
from .parsers import parse_raw

logger = logging.getLogger(__name__)


class DataIngestion:
    """Turns raw source payloads into governance-checked ``RawIncident``s."""

    def __init__(self, governance: AIGovernance | None = None) -> None:
        self._governance = governance or AIGovernance()

    def ingest(self, payload: dict[str, Any]) -> tuple[RawIncident, list[str]]:
        """Parse, sanitize, and return ``(incident, warnings)``."""
        incident = parse_raw(payload)
        result = self._governance.sanitize(incident.content)
        incident.content = result.safe_text
        # Store only non-reversible PII stats on the incident. The token->value
        # mapping is intentionally dropped here so original PII is never
        # forwarded into downstream LLM prompts or persisted alongside the
        # incident.
        incident.metadata["pii"] = {
            "redacted_count": result.pii_metadata.get("redacted_count", 0),
            "entity_types": result.pii_metadata.get("entity_types", []),
        }
        if result.warnings:
            incident.metadata["guardrail_warnings"] = result.warnings
        return incident, result.warnings

    def ingest_batch(
        self, payloads: list[dict[str, Any]]
    ) -> list[tuple[RawIncident, list[str]]]:
        return [self.ingest(p) for p in payloads]
