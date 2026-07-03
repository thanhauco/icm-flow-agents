"""Application settings loaded from environment variables.

Uses pydantic-settings to provide a single, validated configuration object.
All Azure credentials and runtime tunables are surfaced here so that the rest
of the codebase never reads ``os.environ`` directly.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the ICM Flow Agents system."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------
    # Environment
    # ------------------------------------------------------------------
    environment: Literal["dev", "staging", "production"] = Field(
        default="dev", description="Deployment environment."
    )
    log_level: str = Field(default="INFO", description="Root logging level.")
    azure_client_id: str = Field(
        default="", description="User-assigned managed identity client ID."
    )

    # ------------------------------------------------------------------
    # Azure OpenAI / Foundry
    # ------------------------------------------------------------------
    azure_openai_endpoint: str = Field(
        default="", description="Azure OpenAI / Foundry endpoint URL."
    )
    azure_openai_api_key: str = Field(default="", description="Azure OpenAI API key.")
    azure_openai_api_version: str = Field(default="2024-10-21")
    # Reasoning model used for analysis-heavy agents.
    azure_openai_deployment_name: str = Field(default="gpt-5-2")
    # Interactive model used by the supervisor for orchestration.
    azure_openai_chat_deployment_name: str = Field(default="gpt-5-2-chat")
    azure_openai_embedding_deployment: str = Field(
        default="text-embedding-3-large"
    )

    # ------------------------------------------------------------------
    # Azure AI Search (vector store)
    # ------------------------------------------------------------------
    azure_ai_search_endpoint: str = Field(default="")
    azure_ai_search_key: str = Field(default="")
    azure_ai_search_index: str = Field(default="incidents")

    # ------------------------------------------------------------------
    # Azure Cosmos DB (memory store)
    # ------------------------------------------------------------------
    azure_cosmos_endpoint: str = Field(default="")
    azure_cosmos_connection_string: str = Field(default="")
    azure_cosmos_database: str = Field(default="icm-flow-agents")
    azure_cosmos_memory_container: str = Field(default="agent-memory")
    azure_cosmos_history_container: str = Field(default="execution-history")

    # ------------------------------------------------------------------
    # Azure AI Language (PII detection)
    # ------------------------------------------------------------------
    azure_ai_language_endpoint: str = Field(default="")
    azure_ai_language_key: str = Field(default="")

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------
    applicationinsights_connection_string: str = Field(
        default="", description="Application Insights connection string."
    )

    # ------------------------------------------------------------------
    # Runtime tunables
    # ------------------------------------------------------------------
    request_timeout_seconds: int = Field(default=60)
    max_retries: int = Field(default=3)
    noise_filter_threshold: int = Field(
        default=70, description="Noise score above which an incident is filtered."
    )
    max_cost_per_incident_usd: float = Field(default=1.0)
    enable_telemetry: bool = Field(default=True)

    # ------------------------------------------------------------------
    # Auto triage & mitigation
    # ------------------------------------------------------------------
    auto_triage_enabled: bool = Field(
        default=True, description="Run the Auto-Triage engine after mitigation."
    )
    auto_mitigation_enabled: bool = Field(
        default=True, description="Allow auto-execution of low-risk mitigation actions."
    )
    auto_escalation_team: str = Field(
        default="on-call-sre", description="Team paged when an incident is escalated."
    )

    # ------------------------------------------------------------------
    # NVIDIA Build (OpenAI-compatible) — used for chat when nvidia_api_key is set.
    # ------------------------------------------------------------------
    nvidia_api_key: str = Field(default="")
    nvidia_base_url: str = Field(default="https://integrate.api.nvidia.com/v1")
    nvidia_model: str = Field(default="z-ai/glm-5.2")

    @property
    def has_nvidia(self) -> bool:
        """Whether NVIDIA Build (OpenAI-compatible) is configured."""
        return bool(self.nvidia_api_key)

    @property
    def has_azure_openai(self) -> bool:
        """Whether live Azure OpenAI credentials are configured."""
        return bool(self.azure_openai_endpoint)

    @property
    def has_vector_store(self) -> bool:
        return bool(self.azure_ai_search_endpoint)

    @property
    def has_cosmos(self) -> bool:
        return bool(self.azure_cosmos_endpoint or self.azure_cosmos_connection_string)

    @property
    def has_language_service(self) -> bool:
        return bool(self.azure_ai_language_endpoint and self.azure_ai_language_key)

    @property
    def has_telemetry(self) -> bool:
        return bool(
            self.enable_telemetry and self.applicationinsights_connection_string
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton ``Settings`` instance."""
    return Settings()
