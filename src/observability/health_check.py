"""Health checks for the system and its external dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import get_settings


@dataclass
class HealthStatus:
    healthy: bool
    components: dict[str, str] = field(default_factory=dict)


class HealthCheck:
    """Reports configuration/readiness of external dependencies."""

    def check(self) -> HealthStatus:
        settings = get_settings()
        components = {
            "azure_openai": "configured" if settings.has_azure_openai else "offline-stub",
            "vector_store": "configured" if settings.has_vector_store else "in-memory",
            "cosmos_db": "configured" if settings.has_cosmos else "in-memory",
            "language_service": "configured"
            if settings.has_language_service
            else "regex-fallback",
        }
        # The system is always "healthy" because every dependency has a local
        # fallback; degraded components are surfaced for visibility.
        return HealthStatus(healthy=True, components=components)
