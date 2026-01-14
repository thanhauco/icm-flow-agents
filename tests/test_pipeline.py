"""End-to-end pipeline tests using the offline LLM stub."""

import pytest

from src.core import LLMClient
from src.pipeline import IncidentPipeline


@pytest.mark.asyncio
async def test_pipeline_processes_outage():
    pipeline = IncidentPipeline(llm=LLMClient())
    result, report = await pipeline.run(
        {
            "source": "email",
            "content": "Production database is down, outage affecting all users.",
        }
    )
    assert not result.filtered_as_noise
    assert result.impact is not None
    assert result.mitigation is not None
    assert result.mitigation.immediate_actions
    assert report.passed
    persisted = pipeline.memory.fetch(result.incident.incident_id)
    assert persisted is not None
    assert persisted["evaluation"]["passed"] is True


@pytest.mark.asyncio
async def test_pipeline_filters_noise():
    pipeline = IncidentPipeline(llm=LLMClient())
    result, report = await pipeline.run(
        {"source": "chat", "content": "TEST alert flapping, please ignore duplicate."}
    )
    assert result.filtered_as_noise
    assert result.noise is not None
    assert result.noise.is_noise


@pytest.mark.asyncio
async def test_pipeline_redacts_pii_before_processing():
    pipeline = IncidentPipeline(llm=LLMClient())
    result, _ = await pipeline.run(
        {
            "source": "email",
            "content": "Outage reported by john.doe@example.com on api-gateway.",
        }
    )
    assert "john.doe@example.com" not in result.incident.description


@pytest.mark.asyncio
async def test_supervisor_batch():
    pipeline = IncidentPipeline(llm=LLMClient())
    out = await pipeline.run_batch(
        [
            {"source": "email", "content": "Database outage, critical."},
            {"source": "chat", "content": "TEST ignore this duplicate."},
        ]
    )
    assert len(out) == 2
