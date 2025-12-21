"""In-memory + optional Cosmos-backed memory manager.

Provides short-term (session) and long-term (historical) storage. When Cosmos
DB is not configured, an in-process dictionary store is used so the system runs
locally. The interface is intentionally small so a Cosmos implementation can be
dropped in behind it.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from ..config import get_settings
from .azure_credentials import get_azure_credential

logger = logging.getLogger(__name__)


class MemoryManager:
    """Short- and long-term memory with TTL-based short-term eviction."""

    def __init__(self, short_term_ttl_seconds: int = 900) -> None:
        self._settings = get_settings()
        self._short_term: dict[str, tuple[float, Any]] = {}
        self._long_term: dict[str, Any] = {}
        self._ttl = short_term_ttl_seconds
        self._cosmos_container: Any | None = None

        if self._settings.has_cosmos:
            self._cosmos_container = self._create_cosmos_container()
            if self._cosmos_container is not None:
                logger.info("Memory manager configured for Azure Cosmos DB.")
            else:
                logger.info("Memory manager falling back to in-memory mode.")

    # -- short-term -----------------------------------------------------
    def remember(self, key: str, value: Any) -> None:
        self._short_term[key] = (time.monotonic(), value)

    def recall(self, key: str) -> Any | None:
        entry = self._short_term.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.monotonic() - ts > self._ttl:
            del self._short_term[key]
            return None
        return value

    # -- long-term ------------------------------------------------------
    def persist(self, key: str, value: Any) -> None:
        self._long_term[key] = value
        if self._cosmos_container is not None:
            try:
                item = {
                    "id": key,
                    "type": "memory",
                    "value": _json_compatible(value),
                    "updated_at": time.time(),
                }
                self._cosmos_container.upsert_item(item)
            except Exception as exc:  # noqa: BLE001 - keep pipeline available
                logger.warning("Cosmos memory persist failed for %s: %s", key, exc)
        logger.debug("Persisted long-term memory: %s", key)

    def fetch(self, key: str) -> Any | None:
        if self._cosmos_container is not None:
            try:
                item = self._cosmos_container.read_item(item=key, partition_key=key)
                return item.get("value")
            except Exception as exc:  # noqa: BLE001 - SDK returns several exception types
                logger.debug("Cosmos memory fetch miss for %s: %s", key, exc)
        return self._long_term.get(key)

    def history(self) -> list[Any]:
        if self._cosmos_container is not None:
            try:
                query = (
                    "SELECT TOP 100 c.value FROM c "
                    "WHERE c.type = @type ORDER BY c.updated_at DESC"
                )
                params = [{"name": "@type", "value": "memory"}]
                return [
                    item["value"]
                    for item in self._cosmos_container.query_items(
                        query=query,
                        parameters=params,
                        enable_cross_partition_query=True,
                    )
                ]
            except Exception as exc:  # noqa: BLE001 - keep fallback available
                logger.warning("Cosmos memory history query failed: %s", exc)
        return list(self._long_term.values())

    def _create_cosmos_container(self) -> Any | None:
        try:
            from azure.cosmos import CosmosClient, PartitionKey

            if self._settings.azure_cosmos_connection_string:
                client = CosmosClient.from_connection_string(
                    self._settings.azure_cosmos_connection_string
                )
                database = client.create_database_if_not_exists(
                    id=self._settings.azure_cosmos_database
                )
                return database.create_container_if_not_exists(
                    id=self._settings.azure_cosmos_memory_container,
                    partition_key=PartitionKey(path="/id"),
                )
            else:
                client = CosmosClient(
                    self._settings.azure_cosmos_endpoint,
                    credential=get_azure_credential(),
                )
                database = client.get_database_client(self._settings.azure_cosmos_database)
                return database.get_container_client(
                    self._settings.azure_cosmos_memory_container
                )
        except Exception as exc:  # pragma: no cover - depends on Azure SDK/cloud
            logger.warning("Cosmos DB initialization failed: %s", exc)
            return None


def _json_compatible(value: Any) -> Any:
    """Convert values such as datetimes/Pydantic models into JSON types."""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.loads(json.dumps(value, default=str))
