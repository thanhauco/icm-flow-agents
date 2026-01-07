"""Optional Azure Monitor / OpenTelemetry instrumentation.

Telemetry is configured only when an Application Insights connection string is
present. Without it, ``configure_telemetry`` is a no-op so local runs and tests
have zero external dependencies. Configuration is idempotent.
"""

from __future__ import annotations

import logging

from ..config import get_settings

logger = logging.getLogger(__name__)

_configured = False


def configure_telemetry(app: object | None = None) -> bool:
    """Configure Azure Monitor OpenTelemetry if a connection string is set.

    Args:
        app: Optional FastAPI app to auto-instrument.

    Returns:
        ``True`` if telemetry was configured, ``False`` otherwise.
    """
    global _configured
    if _configured:
        return True

    settings = get_settings()
    if not settings.has_telemetry:
        logger.debug("Telemetry disabled (no connection string).")
        return False

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor(
            connection_string=settings.applicationinsights_connection_string,
            logger_name="src",
        )
        if app is not None:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

                FastAPIInstrumentor.instrument_app(app)
            except Exception as exc:  # pragma: no cover - optional dependency
                logger.warning("FastAPI auto-instrumentation skipped: %s", exc)

        _configured = True
        logger.info("Azure Monitor telemetry configured.")
        return True
    except Exception as exc:  # pragma: no cover - import/config guard
        logger.warning("Telemetry configuration failed: %s", exc)
        return False
