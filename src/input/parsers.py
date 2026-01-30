"""Parsers that convert source payloads into ``RawIncident`` objects."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..core.models import RawIncident


def parse_raw(payload: dict[str, Any]) -> RawIncident:
    """Normalize a loosely-typed source payload into a ``RawIncident``.

    Accepts common field aliases (``body``/``text``/``message`` for content,
    ``channel``/``source`` for origin) so different ingestion channels can feed
    the same pipeline.
    """
    content = (
        payload.get("content")
        or payload.get("body")
        or payload.get("text")
        or payload.get("message")
        or ""
    )
    source = payload.get("source") or payload.get("channel") or "unknown"

    ts = payload.get("timestamp")
    if isinstance(ts, str):
        try:
            timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            timestamp = datetime.now(timezone.utc)
    elif isinstance(ts, datetime):
        timestamp = ts
    else:
        timestamp = datetime.now(timezone.utc)

    metadata = {
        k: v
        for k, v in payload.items()
        if k not in {"content", "body", "text", "message", "source", "channel", "timestamp"}
    }
    return RawIncident(
        source=str(source), content=str(content), timestamp=timestamp, metadata=metadata
    )

# Streamlined log line parsers for nested formats

# Streamlined log line parsers for nested formats
