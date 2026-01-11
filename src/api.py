"""FastAPI application exposing the incident pipeline as a REST API.

Run locally with:

    uvicorn src.api:app --reload --port 8000

The pipeline is created once at startup and reused across requests. It runs in
offline-stub mode unless Azure credentials are configured.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api_models import (
    BatchIncidentRequest,
    EvaluationModel,
    HealthResponse,
    IncidentRequest,
    IncidentResponse,
)
from .config import get_settings
from .core.models import IncidentResult
from .governance import GuardrailViolation
from .observability import HealthCheck, configure_telemetry
from .output import EvaluationReport
from .output.formatters import to_summary_dict
from .pipeline import IncidentPipeline

logger = logging.getLogger(__name__)

_WEB_DIR = Path(__file__).parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared resources on startup."""
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    )
    configure_telemetry(app)
    app.state.pipeline = IncidentPipeline()
    logger.info("ICM Flow Agents API ready (live LLM=%s).", app.state.pipeline.llm.is_live)
    yield


app = FastAPI(
    title="ICM Flow Agents API",
    description="Multi-agent incident management system.",
    version="0.1.0",
    lifespan=lifespan,
)


def _build_detail(result: IncidentResult) -> dict:
    """Serialize full per-agent output for the web UI."""
    return {
        "source": result.incident.source,
        "description": result.incident.description,
        "affected_services": result.incident.affected_services,
        "keywords": result.incident.keywords,
        "plan": result.plan.model_dump(mode="json") if result.plan else None,
        "noise": result.noise.model_dump(mode="json") if result.noise else None,
        "impact": result.impact.model_dump(mode="json") if result.impact else None,
        "mitigation": (
            result.mitigation.model_dump(mode="json") if result.mitigation else None
        ),
        "triage": result.triage.model_dump(mode="json") if result.triage else None,
    }


def _to_response(
    result: IncidentResult, report: EvaluationReport
) -> IncidentResponse:
    summary = to_summary_dict(result)
    return IncidentResponse(
        **summary,
        evaluation=EvaluationModel(
            passed=report.passed, score=report.score, issues=report.issues
        ),
        detail=_build_detail(result),
    )


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """Serve the single-page dashboard."""
    return FileResponse(_WEB_DIR / "index.html")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report system and dependency readiness."""
    status = HealthCheck().check()
    return HealthResponse(healthy=status.healthy, components=status.components)


@app.post("/incidents", response_model=IncidentResponse)
async def process_incident(request: IncidentRequest) -> IncidentResponse:
    """Process a single incident end-to-end."""
    pipeline: IncidentPipeline = app.state.pipeline
    try:
        result, report = await pipeline.run(request.to_payload())
    except GuardrailViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface as 500 with detail
        logger.exception("Incident processing failed.")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _to_response(result, report)


@app.post("/incidents/batch", response_model=list[IncidentResponse])
async def process_batch(request: BatchIncidentRequest) -> list[IncidentResponse]:
    """Process multiple incidents sequentially."""
    pipeline: IncidentPipeline = app.state.pipeline
    responses: list[IncidentResponse] = []
    for incident in request.incidents:
        try:
            result, report = await pipeline.run(incident.to_payload())
        except GuardrailViolation as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        responses.append(_to_response(result, report))
    return responses


@app.get("/metrics")
async def metrics() -> dict:
    """Expose cost and aggregate triage/usage analytics."""
    pipeline: IncidentPipeline = app.state.pipeline
    data = {
        "total_cost_usd": round(pipeline.cost_tracker.total_usd, 6),
        "live_llm": pipeline.llm.is_live,
    }
    data.update(pipeline.metrics.snapshot())
    return data


@app.post("/incidents/{incident_id}/approve")
async def approve_actions(incident_id: str) -> dict:
    """Approve and execute the pending mitigation actions for an incident."""
    pipeline: IncidentPipeline = app.state.pipeline
    decision = pipeline.approve_pending(incident_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="No pending triage for incident.")
    return decision.model_dump(mode="json")


# Serve static assets (favicon, future JS/CSS) from the web directory.
app.mount("/static", StaticFiles(directory=str(_WEB_DIR)), name="static")
