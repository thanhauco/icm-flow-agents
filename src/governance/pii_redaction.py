"""PII detection and redaction.

A dependency-light implementation that uses regex patterns for fast, offline
PII detection with tokenization or masking strategies. Mirrors the design in
``docs/ARCHITECTURE.md`` while remaining runnable without Azure AI Language.
"""

from __future__ import annotations

import logging
import re
from typing import Literal

logger = logging.getLogger(__name__)

RedactionStrategy = Literal["tokenize", "mask", "remove"]

# Common PII regex patterns. Order matters only for readability; overlapping
# matches are resolved during de-duplication.
_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "employee_id": re.compile(r"\bEMP-\d{6}\b"),
}


class PIIRedactionService:
    """Detect and redact PII from free text."""

    def detect_and_redact(
        self, text: str, strategy: RedactionStrategy = "tokenize"
    ) -> tuple[str, dict]:
        """Return ``(redacted_text, metadata)``.

        ``metadata`` includes the redacted entity types and, for the
        ``tokenize`` strategy, a mapping from token back to original value so
        authorized downstream consumers can re-hydrate the text.
        """
        entities = self._detect(text)
        entities = self._deduplicate(entities)

        redacted = text
        offset = 0
        counters: dict[str, int] = {}
        token_mapping: dict[str, str] = {}
        redacted_types: list[str] = []

        for ent in entities:
            start = ent["start"] + offset
            end = ent["end"] + offset
            original = ent["text"]
            etype = ent["type"]

            if strategy == "tokenize":
                counters[etype] = counters.get(etype, 0) + 1
                replacement = f"[{etype.upper()}_{counters[etype]}]"
                token_mapping[replacement] = original
            elif strategy == "mask":
                replacement = self._mask(original, etype)
            else:  # remove
                replacement = ""

            redacted = redacted[:start] + replacement + redacted[end:]
            offset += len(replacement) - (end - start)
            redacted_types.append(etype)

        metadata = {
            "redacted_count": len(entities),
            "entity_types": sorted(set(redacted_types)),
            "token_mapping": token_mapping,
        }
        if entities:
            logger.info(
                "PII redaction applied: %d entities (%s)",
                len(entities),
                ", ".join(metadata["entity_types"]),
            )
        return redacted, metadata

    def _detect(self, text: str) -> list[dict]:
        entities: list[dict] = []
        for etype, pattern in _PATTERNS.items():
            for match in pattern.finditer(text):
                entities.append(
                    {
                        "type": etype,
                        "text": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                    }
                )
        return entities

    @staticmethod
    def _deduplicate(entities: list[dict]) -> list[dict]:
        """Remove overlapping matches, keeping the earliest/longest."""
        if not entities:
            return []
        entities.sort(key=lambda e: (e["start"], -(e["end"] - e["start"])))
        result: list[dict] = []
        last_end = -1
        for ent in entities:
            if ent["start"] >= last_end:
                result.append(ent)
                last_end = ent["end"]
        return result

    @staticmethod
    def _mask(text: str, etype: str) -> str:
        digits = re.sub(r"\D", "", text)
        if etype == "ssn":
            return f"***-**-{digits[-4:]}"
        if etype == "credit_card":
            return f"****-****-****-{digits[-4:]}"
        if etype == "phone":
            return f"***-***-{digits[-4:]}"
        return "*" * len(text)
