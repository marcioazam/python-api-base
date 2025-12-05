"""Dapr configuration settings.

This module provides configuration for Dapr sidecar integration.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DaprSettings(BaseSettings):
    """Dapr configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="DAPR_",
        env_file=".env",
        extra="ignore",
    )

    enabled: bool = Field(
        default=True,
        description="Enable Dapr integration",
    )
    http_endpoint: str = Field(
        default="http://localhost:3500",
        description="Dapr HTTP endpoint",
    )
    grpc_endpoint: str = Field(
        default="localhost:50001",
        description="Dapr gRPC endpoint",
    )
    api_token: str | None = Field(
        default=None,
        description="Dapr API token for authentication",
    )
    app_id: str = Field(
        default="python-api",
        description="Application ID for Dapr",
    )
    app_port: int = Field(
        default=8000,
        description="Application port for Dapr callbacks",
    )
    timeout_seconds: int = Field(
        default=60,
        description="Default timeout for Dapr operations",
    )
    state_store_name: str = Field(
        default="statestore",
        description="Default state store component name",
    )
    pubsub_name: str = Field(
        default="pubsub",
        description="Default pub/sub component name",
    )
    secret_store_name: str = Field(
        default="secretstore",
        description="Default secret store component name",
    )
    health_check_enabled: bool = Field(
        default=True,
        description="Enable Dapr health checks",
    )
    wait_for_sidecar: bool = Field(
        default=True,
        description="Wait for sidecar on startup",
    )
    sidecar_wait_timeout: int = Field(
        default=60,
        description="Timeout for waiting for sidecar",
    )
    tracing_enabled: bool = Field(
        default=True,
        description="Enable distributed tracing",
    )
    metrics_enabled: bool = Field(
        default=True,
        description="Enable Prometheus metrics",
    )


_dapr_settings: DaprSettings | None = None


def get_dapr_settings() -> DaprSettings:
    """Get Dapr settings singleton."""
    global _dapr_settings
    if _dapr_settings is None:
        _dapr_settings = DaprSettings()
    return _dapr_settings
