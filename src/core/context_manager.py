"""Context manager: tracks per-session incident state and history."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .memory_manager import MemoryManager

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """Mutable state for a single processing session."""

    session_id: str
    environment: str = "dev"
    active_incidents: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """Manages session lifecycle and bridges to the memory manager."""

    def __init__(self, memory: MemoryManager | None = None) -> None:
        self._memory = memory or MemoryManager()
        self._sessions: dict[str, SessionContext] = {}

    def create_session(self, session_id: str, environment: str = "dev") -> SessionContext:
        ctx = SessionContext(session_id=session_id, environment=environment)
        self._sessions[session_id] = ctx
        logger.debug("Created session %s (%s)", session_id, environment)
        return ctx

    def get_session(self, session_id: str) -> SessionContext | None:
        return self._sessions.get(session_id)

    def track_incident(self, session_id: str, incident_id: str) -> None:
        ctx = self._sessions.setdefault(
            session_id, SessionContext(session_id=session_id)
        )
        ctx.active_incidents.append(incident_id)
        self._memory.remember(f"{session_id}:{incident_id}", {"status": "active"})

    @property
    def memory(self) -> MemoryManager:
        return self._memory
