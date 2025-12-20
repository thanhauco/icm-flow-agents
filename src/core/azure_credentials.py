"""Credential helpers for Azure SDK clients.

Production deployments use the user-assigned managed identity exposed through
``AZURE_CLIENT_ID``. Local development falls back to DefaultAzureCredential with
interactive browser disabled.
"""

from __future__ import annotations

from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

from ..config import get_settings


def get_azure_credential() -> TokenCredential:
    """Return the preferred Azure token credential for data-plane clients."""
    settings = get_settings()
    if settings.azure_client_id:
        return ManagedIdentityCredential(client_id=settings.azure_client_id)
    return DefaultAzureCredential(exclude_interactive_browser_credential=True)
