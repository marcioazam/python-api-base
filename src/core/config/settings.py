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

# Rate limit pattern: number/unit (e.g., "100/minute", "10/second")
RATE_LIMIT_PATTERN: Final = re.compile(r"^\d+/(second|minute|hour|day)$")


def redact_url_credentials(url: str) -> str:
    """Redact credentials from a URL for safe logging.

    Args:
        url: URL that may contain credentials.

    Returns:
        URL with password replaced by [REDACTED].
    """
    try:
        parsed = urlparse(url)
        if parsed.password:
            # Replace password in netloc
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
    max_overflow: int = Field(
        default=10, ge=0, le=100, description="Max overflow connections"
    )
    echo: bool = Field(default=False, description="Echo SQL statements")

    def get_safe_url(self) -> str:
        """Get URL with credentials redacted for logging."""
        return redact_url_credentials(self.url)

    def __repr__(self) -> str:
        """Safe representation without credentials."""
        return (
            f"DatabaseSettings(url='{self.get_safe_url()}', pool_size={self.pool_size})"
        )


class SecuritySettings(BaseSettings):
    """Security configuration settings.

    **Feature: core-code-review**
    **Validates: Requirements 1.1, 1.2, 1.4**
    """

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
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, ge=1, description="Access token expiration in minutes"
    )
    # Security headers configuration
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
        """Validate secret key has sufficient entropy (256 bits = 32 chars).

        **Feature: core-code-review, Property 1: Secret Key Entropy Validation**
        **Validates: Requirements 1.1**
        """
        secret = v.get_secret_value()
        if len(secret) < 32:
            raise ValueError(
                "Secret key must be at least 32 characters (256 bits) for security"
            )
        return v

    @field_validator("cors_origins")
    @classmethod
    def warn_wildcard_cors(cls, v: list[str]) -> list[str]:
        """Warn about wildcard CORS in production.

        **Feature: core-code-review**
        **Validates: Requirements 1.2**
        """
        if "*" in v:
            env = os.getenv("ENVIRONMENT", "").lower()
            if env == "production":
                logger.warning(
                    "SECURITY WARNING: Wildcard CORS origin '*' detected in production. "
                    "This allows any origin to make requests to your API."
                )
        return v

    @field_validator("rate_limit")
    @classmethod
    def validate_rate_limit_format(cls, v: str) -> str:
        """Validate rate limit format.

        **Feature: core-code-review**
        **Validates: Requirements 1.4**
        """
        if not RATE_LIMIT_PATTERN.match(v):
            raise ValueError(
                f"Invalid rate limit format: '{v}'. "
                "Expected format: 'number/unit' (e.g., '100/minute', '10/second')"
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
        description="Enable Redis for token storage (uses in-memory if disabled)",
    )
    token_ttl: int = Field(
        default=604800,
        ge=60,
        description="Default token TTL in seconds (7 days)",
    )


class ObservabilitySettings(BaseSettings):
    """Observability configuration settings.

    **Feature: observability-infrastructure**
    **Requirement: R12 - Configuration Management**
    """

    model_config = SettingsConfigDict(env_prefix="OBSERVABILITY__")

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )
    log_format: str = Field(
        default="json",
        description="Log output format (json or console)",
        pattern="^(json|console)$",
    )
    log_ecs_format: bool = Field(
        default=True,
        description="Use ECS-compatible field names in logs",
    )
    log_pii_redaction: bool = Field(
        default=True,
        description="Enable automatic PII redaction in logs",
    )

    # OpenTelemetry
    otlp_endpoint: str | None = Field(
        default=None,
        description="OpenTelemetry collector endpoint",
    )
    service_name: str = Field(
        default="python-api-base",
        description="Service name for tracing and logging",
    )
    service_version: str = Field(
        default="1.0.0",
        description="Service version for tracing",
    )
    environment: str = Field(
        default="development",
        description="Environment name (development, staging, production)",
    )
    enable_tracing: bool = Field(default=True, description="Enable distributed tracing")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")

    # Elasticsearch
    elasticsearch_enabled: bool = Field(
        default=False,
        description="Enable log shipping to Elasticsearch",
    )
    elasticsearch_hosts: list[str] = Field(
        default=["http://localhost:9200"],
        description="Elasticsearch hosts",
    )
    elasticsearch_index_prefix: str = Field(
        default="logs-python-api-base",
        description="Prefix for Elasticsearch index names",
    )
    elasticsearch_username: str | None = Field(
        default=None,
        description="Elasticsearch username",
    )
    elasticsearch_password: SecretStr | None = Field(
        default=None,
        description="Elasticsearch password",
    )
    elasticsearch_api_key: SecretStr | None = Field(
        default=None,
        description="Elasticsearch API key (alternative to username/password)",
    )
    elasticsearch_use_ssl: bool = Field(
        default=False,
        description="Use SSL for Elasticsearch connection",
    )
    elasticsearch_verify_certs: bool = Field(
        default=True,
        description="Verify SSL certificates",
    )
    elasticsearch_batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Number of logs to batch before sending to Elasticsearch",
    )
    elasticsearch_flush_interval: float = Field(
        default=5.0,
        ge=1.0,
        le=60.0,
        description="Max seconds between Elasticsearch flushes",
    )

    # Kafka
    kafka_enabled: bool = Field(
        default=False,
        description="Enable Kafka integration",
    )
    kafka_bootstrap_servers: list[str] = Field(
        default=["localhost:9092"],
        description="Kafka bootstrap servers",
    )
    kafka_client_id: str = Field(
        default="python-api-base",
        description="Kafka client ID",
    )
    kafka_group_id: str = Field(
        default="python-api-base-group",
        description="Kafka consumer group ID",
    )
    kafka_auto_offset_reset: str = Field(
        default="earliest",
        description="Kafka auto offset reset (earliest, latest)",
        pattern="^(earliest|latest)$",
    )
    kafka_enable_auto_commit: bool = Field(
        default=True,
        description="Enable Kafka auto commit",
    )
    kafka_security_protocol: str = Field(
        default="PLAINTEXT",
        description="Kafka security protocol",
    )
    kafka_sasl_mechanism: str | None = Field(
        default=None,
        description="Kafka SASL mechanism",
    )
    kafka_sasl_username: str | None = Field(
        default=None,
        description="Kafka SASL username",
    )
    kafka_sasl_password: SecretStr | None = Field(
        default=None,
        description="Kafka SASL password",
    )

    # ScyllaDB
    scylladb_enabled: bool = Field(
        default=False,
        description="Enable ScyllaDB integration",
    )
    scylladb_hosts: list[str] = Field(
        default=["localhost"],
        description="ScyllaDB contact points",
    )
    scylladb_port: int = Field(
        default=9042,
        description="ScyllaDB port",
    )
    scylladb_keyspace: str = Field(
        default="python_api_base",
        description="ScyllaDB keyspace",
    )
    scylladb_username: str | None = Field(
        default=None,
        description="ScyllaDB username",
    )
    scylladb_password: SecretStr | None = Field(
        default=None,
        description="ScyllaDB password",
    )
    scylladb_protocol_version: int = Field(
        default=4,
        description="CQL protocol version",
    )
    scylladb_connect_timeout: int = Field(
        default=10,
        description="Connection timeout in seconds",
    )
    scylladb_request_timeout: int = Field(
        default=30,
        description="Request timeout in seconds",
    )

    # Prometheus
    prometheus_enabled: bool = Field(
        default=True,
        description="Enable Prometheus metrics",
    )
    prometheus_endpoint: str = Field(
        default="/metrics",
        description="Prometheus metrics endpoint",
    )
    prometheus_include_in_schema: bool = Field(
        default=False,
        description="Include metrics endpoint in OpenAPI schema",
    )
    prometheus_namespace: str = Field(
        default="python_api",
        description="Prometheus metrics namespace",
    )
    prometheus_subsystem: str = Field(
        default="",
        description="Prometheus metrics subsystem",
    )

    # Redis
    redis_enabled: bool = Field(
        default=False,
        description="Enable Redis cache",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_pool_size: int = Field(
        default=10,
        description="Redis connection pool size",
    )
    redis_key_prefix: str = Field(
        default="api",
        description="Redis key prefix",
    )

    # MinIO
    minio_enabled: bool = Field(
        default=False,
        description="Enable MinIO storage",
    )
    minio_endpoint: str = Field(
        default="localhost:9000",
        description="MinIO endpoint",
    )
    minio_access_key: str = Field(
        default="minioadmin",
        description="MinIO access key",
    )
    minio_secret_key: SecretStr = Field(
        default="minioadmin",
        description="MinIO secret key",
    )
    minio_bucket: str = Field(
        default="uploads",
        description="MinIO default bucket",
    )
    minio_secure: bool = Field(
        default=False,
        description="Use HTTPS for MinIO",
    )

    # RabbitMQ
    rabbitmq_enabled: bool = Field(
        default=False,
        description="Enable RabbitMQ task queue",
    )
    rabbitmq_host: str = Field(
        default="localhost",
        description="RabbitMQ host",
    )
    rabbitmq_port: int = Field(
        default=5672,
        description="RabbitMQ port",
    )
    rabbitmq_username: str = Field(
        default="guest",
        description="RabbitMQ username",
    )
    rabbitmq_password: SecretStr = Field(
        default="guest",
        description="RabbitMQ password",
    )
    rabbitmq_virtual_host: str = Field(
        default="/",
        description="RabbitMQ virtual host",
    )

    # Keycloak
    keycloak_enabled: bool = Field(
        default=False,
        description="Enable Keycloak OAuth",
    )
    keycloak_server_url: str = Field(
        default="http://localhost:8080",
        description="Keycloak server URL",
    )
    keycloak_realm: str = Field(
        default="master",
        description="Keycloak realm",
    )
    keycloak_client_id: str = Field(
        default="python-api",
        description="Keycloak client ID",
    )
    keycloak_client_secret: SecretStr = Field(
        default="",
        description="Keycloak client secret",
    )


class Settings(BaseSettings):
    """Application settings with nested configuration."""

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

    # Nested settings
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
