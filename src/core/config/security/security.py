"""Security configuration settings.

**Feature: core-code-review**
**Refactored: 2025 - Extracted from settings.py for SRP compliance**
**Validates: Requirements 1.1, 1.2, 1.4**
"""

import logging
import os
import re
from typing import Final

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Rate limit pattern: number/unit (e.g., "100/minute", "10/second")
RATE_LIMIT_PATTERN: Final = re.compile(r"^\d+/(second|minute|hour|day)$")


class SecuritySettings(BaseSettings):
    """Security configuration settings."""

    model_config = SettingsConfigDict(env_prefix="SECURITY__")

    secret_key: SecretStr = Field(
        ...,
        description="Secret key for signing tokens (min 256-bit entropy)",
        min_length=32,
    )
    cors_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins",
    )
    rate_limit: str = Field(
        default="100/minute",
        description="Rate limit configuration (format: number/unit)",
    )
    algorithm: str = Field(default="RS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, ge=1, description="Access token expiration in minutes"
    )
    csp: str = Field(
        default="default-src 'self'",
        description="Content-Security-Policy header value",
    )
    permissions_policy: str = Field(
        default="geolocation=(), microphone=(), camera=()",
        description="Permissions-Policy header value",
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_entropy(cls, v: SecretStr) -> SecretStr:
        """Validate secret key has sufficient entropy (256 bits = 32 chars)."""
        secret = v.get_secret_value()
        if len(secret) < 32:
            raise ValueError(
                "Secret key must be at least 32 characters (256 bits) for security"
            )
        return v

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: list[str]) -> list[str]:
        """Validate CORS origins - block wildcard in production and staging."""
        if "*" in v:
            env = os.getenv("ENVIRONMENT", "").lower()
            restricted_envs = {"production", "staging", "prod", "stg"}
            if env in restricted_envs:
                raise ValueError(
                    f"SECURITY: Wildcard CORS origin '*' is not allowed in {env}. "
                    "Specify explicit allowed origins."
                )
            logger.warning(
                "Wildcard CORS origin '*' detected. "
                "This will be blocked in production/staging environments. "
                "Current environment: %s",
                env or "development",
            )
        return v

    @field_validator("rate_limit")
    @classmethod
    def validate_rate_limit_format(cls, v: str) -> str:
        """Validate rate limit format."""
        if not RATE_LIMIT_PATTERN.match(v):
            raise ValueError(
                f"Invalid rate limit format: '{v}'. "
                "Expected format: 'number/unit' (e.g., '100/minute')"
            )
        return v


class RedisSettings(BaseSettings):
    """Redis configuration settings for token storage."""

    model_config = SettingsConfigDict(env_prefix="REDIS__")

    url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    enabled: bool = Field(
        default=False,
        description="Enable Redis for token storage",
    )
    token_ttl: int = Field(
        default=604800,
        ge=60,
        description="Default token TTL in seconds (7 days)",
    )
