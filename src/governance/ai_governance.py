"""AI governance facade combining PII redaction and guardrails."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .guardrails import Guardrails
from .pii_redaction import PIIRedactionService, RedactionStrategy

logger = logging.getLogger(__name__)


@dataclass
class GovernanceResult:
    """Outcome of running text through the governance pipeline."""

    safe_text: str
    warnings: list[str] = field(default_factory=list)
    pii_metadata: dict = field(default_factory=dict)


class AIGovernance:
    """Single entry point for safety controls applied to incident text."""

    def __init__(self) -> None:
        self._guardrails = Guardrails()
        self._pii = PIIRedactionService()

    def sanitize(
        self, text: str, redaction_strategy: RedactionStrategy = "tokenize"
    ) -> GovernanceResult:
        """Run guardrails then redact PII, returning safe text + metadata."""
        warnings = self._guardrails.check_input(text)
        redacted, pii_meta = self._pii.detect_and_redact(text, redaction_strategy)
        return GovernanceResult(
            safe_text=redacted, warnings=warnings, pii_metadata=pii_meta
        )
