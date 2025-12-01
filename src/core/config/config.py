"""Configuration management with Pydantic Settings.

**Feature: core-code-review**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4**
"""

import logging
import os
import re
from functools import lru_cache
from typing import Annotated, Final
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

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

RATE_LIMIT_PATTERN: Final = re.compile(r"^\d+/(second|minute|hour|day)$")


def redact_url_credentials(url: str) -> str:
    """Redact credentials from a URL for safe logging."""
    try:
        parsed = urlparse(url)
        if parsed.password:
            redacted_netloc = parsed.netloc.replace(
                f":{parsed.password}@", ":[REDACTED]@"
            )
            return url.replace(parsed.netloc, redacted_netloc)
        return url
    except Exception:
        return "[INVALID_URL]"


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    model_config = SettingsConfigDict(env_prefix="DATABASE__")

    url: str = Field(
        default="postgresql+asyncpg://localhost/mydb",
        description="Database connection URL",
    )
    pool_size: int = Field(default=5, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(default=10, ge=0, le=100, description="Max overflow connections")
    echo: bool = Field(default=False, description="Echo SQL statements")

    def get_safe_url(self) -> str:
        return redact_url_credentials(self.url)


class SecuritySettings(BaseSettings):
    """Security configuration settings."""

    model_config = SettingsConfigDict(env_prefix="SECURITY__")

    secret_key: SecretStr = Field(..., description="Secret key for signing tokens", min_length=32)
    cors_origins: list[str] = Field(default=["*"], description="Allowed CORS origins")
    rate_limit: str = Field(default="100/minute", description="Rate limit configuration")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, ge=1, description="Access token expiration")
    csp: str = Field(default="default-src 'self'", description="Content-Security-Policy header")
    permissions_policy: str = Field(default="geolocation=(), microphone=(), camera=()", description="Permissions-Policy header")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_entropy(cls, v: SecretStr) -> SecretStr:
        secret = v.get_secret_value()
        if len(secret) < 32:
            raise ValueError("Secret key must be at least 32 characters")
        return v

    @field_validator("cors_origins")
    @classmethod
    def warn_wildcard_cors(cls, v: list[str]) -> list[str]:
        if "*" in v:
            env = os.getenv("ENVIRONMENT", "").lower()
            if env == "production":
                logger.warning("SECURITY WARNING: Wildcard CORS origin '*' detected in production.")
        return v

    @field_validator("rate_limit")
    @classmethod
    def validate_rate_limit_format(cls, v: str) -> str:
        if not RATE_LIMIT_PATTERN.match(v):
            raise ValueError(f"Invalid rate limit format: '{v}'")
        return v


class RedisSettings(BaseSettings):
    """Redis configuration settings."""

    model_config = SettingsConfigDict(env_prefix="REDIS__")

    url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    enabled: bool = Field(default=False, description="Enable Redis for token storage")
    token_ttl: int = Field(default=604800, ge=60, description="Default token TTL in seconds")


class ObservabilitySettings(BaseSettings):
    """Observability configuration settings."""

    model_config = SettingsConfigDict(env_prefix="OBSERVABILITY__")

    log_level: str = Field(default="INFO", description="Logging level", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_format: str = Field(default="json", description="Log output format", pattern="^(json|console)$")
    otlp_endpoint: str | None = Field(default=None, description="OpenTelemetry collector endpoint")
    service_name: str = Field(default="my-api", description="Service name for tracing")
    enable_tracing: bool = Field(default=True, description="Enable distributed tracing")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")


class Settings(BaseSettings):
    """Application settings with nested configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = Field(default="My API", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    version: str = Field(default="0.1.0", description="API version")
    api_prefix: str = Field(default="/api/v1", description="API route prefix")

    database: Annotated[DatabaseSettings, Field(default_factory=DatabaseSettings)]
    security: Annotated[SecuritySettings, Field(default_factory=SecuritySettings)]
    redis: Annotated[RedisSettings, Field(default_factory=RedisSettings)]
    observability: Annotated[ObservabilitySettings, Field(default_factory=ObservabilitySettings)]


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
