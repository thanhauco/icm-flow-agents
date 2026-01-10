"""Output layer: result evaluation and formatting."""

from .evaluator import Evaluator, EvaluationReport
from .formatters import format_result, to_summary_dict

__all__ = ["Evaluator", "EvaluationReport", "format_result", "to_summary_dict"]
