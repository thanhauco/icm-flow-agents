"""Tests for core models, vector store, memory, and routing."""

from src.core import (
    IncidentType,
    MemoryManager,
    RawIncident,
    Severity,
    StructuredIncident,
    ToolRouter,
    VectorStore,
)


def test_raw_incident_defaults():
    inc = RawIncident(source="email", content="db down")
    assert inc.source == "email"
    assert inc.timestamp is not None


def test_structured_incident_id_format():
    inc = StructuredIncident(title="x")
    assert inc.incident_id.startswith("INC-")


def test_vector_store_search_orders_by_similarity():
    store = VectorStore()
    store.index("a", "database connection timeout production")
    store.index("b", "user interface button color change")
    results = store.search("database timeout in production", top_k=2)
    assert results[0]["id"] == "a"


def test_memory_short_term_roundtrip():
    mem = MemoryManager()
    mem.remember("k", {"v": 1})
    assert mem.recall("k") == {"v": 1}
    assert mem.recall("missing") is None


def test_tool_router_flags_noise_candidate():
    router = ToolRouter()
    inc = StructuredIncident(
        title="TEST alert", keywords=["test"], incident_type=IncidentType.WARNING,
        severity=Severity.P4,
    )
    hints = router.route(inc)
    assert hints["run_noise"] is True
    assert hints["run_mitigation"] is False
