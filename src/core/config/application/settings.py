"""Configuration management with Pydantic Settings.

**Feature: core-code-review**
**Refactored: 2025 - Split into focused modules (457→80 lines)**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4**
"""

from functools import lru_cache
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Import from focused modules
from core.config.infrastructure import DatabaseSettings
from core.config.observability import ObservabilitySettings
from core.config.security import RATE_LIMIT_PATTERN, RedisSettings, SecuritySettings
from core.config.shared import redact_url_credentials

__all__ = [
    "RATE_LIMIT_PATTERN",
    "DatabaseSettings",
    "ObservabilitySettings",
    "RedisSettings",
    "SecuritySettings",
    "Settings",
    "get_settings",
    "redact_url_credentials",
]


class Settings(BaseSettings):
    """Application settings with nested configuration.

    Aggregates all configuration modules into a single settings object.
    Each nested settings class is responsible for its own domain.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # Application settings
    app_name: str = Field(default="My API", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    version: str = Field(default="0.1.0", description="API version")
    api_prefix: str = Field(default="/api/v1", description="API route prefix")

    # Nested settings - each module handles its own configuration
    database: Annotated[DatabaseSettings, Field(default_factory=DatabaseSettings)]
    security: Annotated[SecuritySettings, Field(default_factory=SecuritySettings)]
    redis: Annotated[RedisSettings, Field(default_factory=RedisSettings)]
    observability: Annotated[
        ObservabilitySettings, Field(default_factory=ObservabilitySettings)
    ]


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Settings: Application settings instance.
    """
    return Settings()
