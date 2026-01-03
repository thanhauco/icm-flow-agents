"""Input/output guardrails: injection detection and content validation."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Patterns indicating prompt-injection or jailbreak attempts.
_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions", re.I),
    re.compile(r"disregard\s+(?:the\s+)?(?:system|previous)\s+prompt", re.I),
    re.compile(r"you\s+are\s+now\s+(?:a|an|in)\s+", re.I),
    re.compile(r"reveal\s+(?:your\s+)?(?:system\s+)?prompt", re.I),
    re.compile(r"developer\s+mode", re.I),
    re.compile(r"</?(?:system|assistant|user)>", re.I),
)

MAX_INPUT_CHARS = 50_000


class GuardrailViolation(Exception):
    """Raised when input fails a hard guardrail check."""


class Guardrails:
    """Validates inbound text before it reaches an LLM."""

    def check_input(self, text: str) -> list[str]:
        """Return a list of guardrail warnings (empty means clean).

        Size violations raise ``GuardrailViolation`` because oversized input
        cannot be safely processed; injection attempts are reported as warnings
        so the caller can decide whether to sanitize or reject.
        """
        if not text or not text.strip():
            raise GuardrailViolation("Empty input is not allowed.")
        if len(text) > MAX_INPUT_CHARS:
            raise GuardrailViolation(
                f"Input exceeds maximum size of {MAX_INPUT_CHARS} characters."
            )

        warnings: list[str] = []
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                warning = f"Possible prompt injection: pattern '{pattern.pattern}'"
                logger.warning(warning)
                warnings.append(warning)
        return warnings

    def is_safe(self, text: str) -> bool:
        """Convenience boolean: no injection patterns detected."""
        return not any(p.search(text) for p in _INJECTION_PATTERNS)
