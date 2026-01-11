"""Pydantic request/response models for the REST API.

Kept separate from the internal domain models in ``core.models`` so the public
API contract can evolve independently of internal representations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IncidentRequest(BaseModel):
    """Inbound incident payload accepted by the API."""

    source: str = Field(default="api", description="Origin channel.")
    content: str = Field(..., min_length=1, description="Raw incident text.")
    timestamp: datetime | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source": self.source,
            "content": self.content,
            **self.metadata,
        }
        if self.timestamp is not None:
            payload["timestamp"] = self.timestamp.isoformat()
        return payload


class BatchIncidentRequest(BaseModel):
    incidents: list[IncidentRequest] = Field(..., min_length=1, max_length=100)


class EvaluationModel(BaseModel):
    passed: bool
    score: float
    issues: list[str] = Field(default_factory=list)


class IncidentResponse(BaseModel):
    """API response summarizing a processed incident."""

    incident_id: str
    title: str
    type: str
    severity: str
    filtered_as_noise: bool
    priority: str | None = None
    impact_score: int | None = None
    immediate_actions: list[str] = Field(default_factory=list)
    cost_usd: float
    processing_ms: float
    errors: list[str] = Field(default_factory=list)
    evaluation: EvaluationModel
    #: Full per-agent output (plan, noise, impact, mitigation) for rich UIs.
    detail: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    healthy: bool
    components: dict[str, str]
