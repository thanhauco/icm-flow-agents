"""Quality evaluation of aggregated incident results."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ..core.models import IncidentResult

logger = logging.getLogger(__name__)


@dataclass
class EvaluationReport:
    """Quality verdict for a processed incident."""

    passed: bool
    score: float
    issues: list[str] = field(default_factory=list)


class Evaluator:
    """Heuristic quality gate over an ``IncidentResult``.

    Checks completeness of each stage's output. Returns a 0-1 score and a
    pass/fail verdict the caller can use to trigger retries or escalation.
    """

    def __init__(self, pass_threshold: float = 0.6) -> None:
        self._threshold = pass_threshold

    def evaluate(self, result: IncidentResult) -> EvaluationReport:
        issues: list[str] = []
        checks: list[bool] = []

        # Summarization must produce a usable title and type.
        has_summary = bool(result.incident.title) and result.incident.title != "Untitled incident"
        checks.append(has_summary)
        if not has_summary:
            issues.append("Summarizer produced an empty or default title.")

        if result.filtered_as_noise:
            # A filtered incident is a complete, valid terminal outcome.
            checks.append(result.noise is not None)
            if result.noise is None:
                issues.append("Filtered as noise but no noise result recorded.")
        else:
            if result.plan and result.plan.run_impact:
                ok = result.impact is not None
                checks.append(ok)
                if not ok:
                    issues.append("Impact assessment was planned but missing.")
            if result.plan and result.plan.run_mitigation:
                ok = result.mitigation is not None and bool(
                    result.mitigation.immediate_actions
                )
                checks.append(ok)
                if not ok:
                    issues.append("Mitigation plan missing or has no immediate actions.")

        if result.errors:
            issues.extend(result.errors)
            checks.append(False)

        score = sum(checks) / len(checks) if checks else 0.0
        return EvaluationReport(
            passed=score >= self._threshold and not result.errors,
            score=round(score, 3),
            issues=issues,
        )
