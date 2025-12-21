"""Vector store abstraction for semantic similarity search.

Uses Azure AI Search when configured; otherwise an in-memory cosine-similarity
store over a lightweight hashing embedding. The fallback is deterministic and
dependency-free so similarity search works in local development.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from typing import Any

from ..config import get_settings
from .azure_credentials import get_azure_credential

logger = logging.getLogger(__name__)

_EMBED_DIM = 256


def _hash_embedding(text: str, dim: int = _EMBED_DIM) -> list[float]:
    """Deterministic bag-of-words hashing embedding for offline similarity."""
    vec = [0.0] * dim
    for token in text.lower().split():
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class VectorStore:
    """Semantic search over historical incidents."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._live = self._settings.has_vector_store
        self._docs: list[dict[str, Any]] = []
        self._search_client: Any | None = None
        if self._live:
            self._search_client = self._create_search_client()
            if self._search_client is not None:
                logger.info("Vector store configured for Azure AI Search.")
            else:
                logger.info("Vector store falling back to offline in-memory mode.")
        else:
            logger.info("Vector store running in offline in-memory mode.")

    def index(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        """Add or update a document in the store."""
        doc = {
            "id": doc_id,
            "text": text,
            "embedding": _hash_embedding(text),
            "metadata": metadata or {},
        }
        self._docs.append(doc)

        if self._search_client is not None:
            try:
                self._search_client.upload_documents(
                    [
                        {
                            "id": doc_id,
                            "text": text,
                            "embedding": doc["embedding"],
                            "metadata": json.dumps(metadata or {}, default=str),
                        }
                    ]
                )
            except Exception as exc:  # noqa: BLE001 - keep fallback durable
                logger.warning("Azure AI Search indexing failed: %s", exc)

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Return the ``top_k`` most similar documents to ``query``."""
        if self._search_client is not None:
            results = self._search_azure(query, top_k)
            if results:
                return results

        if not self._docs:
            return []
        q = _hash_embedding(query)
        scored = (
            {
                "id": doc["id"],
                "score": _cosine(q, doc["embedding"]),
                "text": doc["text"],
                "metadata": doc["metadata"],
            }
            for doc in self._docs
        )
        ranked = sorted(scored, key=lambda d: d["score"], reverse=True)
        return ranked[:top_k]

    def _search_azure(self, query: str, top_k: int) -> list[dict[str, Any]]:
        try:
            from azure.search.documents.models import VectorizedQuery

            vector_query = VectorizedQuery(
                vector=_hash_embedding(query),
                k_nearest_neighbors=top_k,
                fields="embedding",
            )
            found = self._search_client.search(
                search_text=query,
                vector_queries=[vector_query],
                top=top_k,
                select=["id", "text", "metadata"],
            )
            return [_search_result_to_dict(item) for item in found]
        except Exception as exc:  # pragma: no cover - requires Azure Search
            logger.warning("Azure AI Search query failed: %s", exc)
            return []

    def _create_search_client(self) -> Any | None:
        try:
            from azure.core.credentials import AzureKeyCredential
            from azure.core.exceptions import ResourceNotFoundError
            from azure.search.documents import SearchClient
            from azure.search.documents.indexes import SearchIndexClient
            from azure.search.documents.indexes.models import (
                HnswAlgorithmConfiguration,
                SearchField,
                SearchFieldDataType,
                SearchIndex,
                SearchableField,
                SimpleField,
                VectorSearch,
                VectorSearchProfile,
            )

            credential: Any = (
                AzureKeyCredential(self._settings.azure_ai_search_key)
                if self._settings.azure_ai_search_key
                else get_azure_credential()
            )
            index_client = SearchIndexClient(
                endpoint=self._settings.azure_ai_search_endpoint,
                credential=credential,
            )
            try:
                index_client.get_index(self._settings.azure_ai_search_index)
            except ResourceNotFoundError:
                index = SearchIndex(
                    name=self._settings.azure_ai_search_index,
                    fields=[
                        SimpleField(
                            name="id",
                            type=SearchFieldDataType.String,
                            key=True,
                            filterable=True,
                        ),
                        SearchableField(name="text", type=SearchFieldDataType.String),
                        SimpleField(name="metadata", type=SearchFieldDataType.String),
                        SearchField(
                            name="embedding",
                            type=SearchFieldDataType.Collection(
                                SearchFieldDataType.Single
                            ),
                            searchable=True,
                            vector_search_dimensions=_EMBED_DIM,
                            vector_search_profile_name="vector-profile",
                        ),
                    ],
                    vector_search=VectorSearch(
                        algorithms=[HnswAlgorithmConfiguration(name="hnsw")],
                        profiles=[
                            VectorSearchProfile(
                                name="vector-profile",
                                algorithm_configuration_name="hnsw",
                            )
                        ],
                    ),
                )
                index_client.create_index(index)

            return SearchClient(
                endpoint=self._settings.azure_ai_search_endpoint,
                index_name=self._settings.azure_ai_search_index,
                credential=credential,
            )
        except Exception as exc:  # pragma: no cover - depends on Azure SDK/cloud
            logger.warning("Azure AI Search initialization failed: %s", exc)
            return None


def _search_result_to_dict(item: Any) -> dict[str, Any]:
    raw = dict(item)
    metadata_text = raw.get("metadata") or "{}"
    try:
        metadata = json.loads(metadata_text)
    except json.JSONDecodeError:
        metadata = {}
    return {
        "id": raw.get("id"),
        "score": raw.get("@search.score", 0.0),
        "text": raw.get("text", ""),
        "metadata": metadata,
    }
