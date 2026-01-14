"""API tests using FastAPI's TestClient against the offline pipeline."""

import pytest
from fastapi.testclient import TestClient

from src.api import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["healthy"] is True
    assert "azure_openai" in body["components"]


def test_index_serves_dashboard(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "ICM Flow Agents" in resp.text


def test_static_index_available(client):
    resp = client.get("/static/index.html")
    assert resp.status_code == 200


def test_process_incident_outage(client):
    resp = client.post(
        "/incidents",
        json={"source": "email", "content": "Production database outage, all users down."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["incident_id"].startswith("INC-")
    assert body["filtered_as_noise"] is False
    assert body["evaluation"]["passed"] is True
    # Enriched detail used by the web UI.
    assert body["detail"] is not None
    assert body["detail"]["impact"] is not None
    assert body["detail"]["mitigation"]["immediate_actions"]


def test_process_incident_noise(client):
    resp = client.post(
        "/incidents",
        json={"source": "chat", "content": "TEST flapping alert, ignore duplicate."},
    )
    assert resp.status_code == 200
    assert resp.json()["filtered_as_noise"] is True


def test_process_incident_rejects_empty_content(client):
    resp = client.post("/incidents", json={"source": "api", "content": ""})
    # Pydantic min_length validation -> 422.
    assert resp.status_code == 422


def test_batch(client):
    resp = client.post(
        "/incidents/batch",
        json={
            "incidents": [
                {"source": "email", "content": "Critical outage on payment-service."},
                {"source": "chat", "content": "TEST ignore duplicate alert."},
            ]
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[1]["filtered_as_noise"] is True


def test_metrics(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "total_cost_usd" in resp.json()


def test_metrics_includes_triage_aggregates(client):
    # Process an incident first so aggregates are populated.
    client.post("/incidents", json={"source": "email", "content": "Critical outage, all users down."})
    resp = client.get("/metrics")
    body = resp.json()
    assert "disposition_counts" in body
    assert body["incidents_total"] >= 1
    assert "auto_actions_executed" in body


def test_incident_includes_triage_detail(client):
    resp = client.post(
        "/incidents",
        json={"source": "email", "content": "Production outage, all services down, ConnectionTimeout."},
    )
    triage = resp.json()["detail"]["triage"]
    assert triage is not None
    assert triage["disposition"] in {
        "auto_resolved", "auto_mitigated", "awaiting_approval", "escalated", "monitor",
    }


def test_approve_endpoint(client):
    created = client.post(
        "/incidents",
        json={"source": "email", "content": "Severe outage, all users impacted."},
    ).json()
    resp = client.post(f"/incidents/{created['incident_id']}/approve")
    assert resp.status_code == 200
    assert "disposition" in resp.json()


def test_approve_unknown_incident_returns_404(client):
    resp = client.post("/incidents/INC-2026-unknown/approve")
    assert resp.status_code == 404
