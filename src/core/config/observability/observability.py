"""Observability configuration settings.

**Feature: observability-infrastructure**
**Refactored: 2025 - Extracted from settings.py for SRP compliance**
"""

from typing import Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ObservabilitySettings(BaseSettings):
    """Observability configuration settings."""

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
    elasticsearch_enabled: bool = Field(default=False)
    elasticsearch_hosts: list[str] = Field(default=["http://localhost:9200"])
    elasticsearch_index_prefix: str = Field(default="logs-python-api-base")
    elasticsearch_username: str | None = Field(default=None)
    elasticsearch_password: SecretStr | None = Field(default=None)
    elasticsearch_api_key: SecretStr | None = Field(default=None)
    elasticsearch_use_ssl: bool = Field(default=False)
    elasticsearch_verify_certs: bool = Field(default=True)
    elasticsearch_batch_size: int = Field(default=100, ge=1, le=1000)
    elasticsearch_flush_interval: float = Field(default=5.0, ge=1.0, le=60.0)

    # Kafka
    kafka_enabled: bool = Field(default=False)
    kafka_bootstrap_servers: list[str] = Field(default=["localhost:9092"])
    kafka_client_id: str = Field(default="python-api-base")
    kafka_group_id: str = Field(default="python-api-base-group")
    kafka_auto_offset_reset: str = Field(
        default="earliest", pattern="^(earliest|latest)$"
    )
    kafka_enable_auto_commit: bool = Field(default=True)
    kafka_security_protocol: str = Field(default="PLAINTEXT")
    kafka_sasl_mechanism: str | None = Field(default=None)
    kafka_sasl_username: str | None = Field(default=None)
    kafka_sasl_password: SecretStr | None = Field(default=None)

    # ScyllaDB
    scylladb_enabled: bool = Field(default=False)
    scylladb_hosts: list[str] = Field(default=["localhost"])
    scylladb_port: int = Field(default=9042)
    scylladb_keyspace: str = Field(default="python_api_base")
    scylladb_username: str | None = Field(default=None)
    scylladb_password: SecretStr | None = Field(default=None)
    scylladb_protocol_version: int = Field(default=4)
    scylladb_connect_timeout: int = Field(default=10)
    scylladb_request_timeout: int = Field(default=30)

    # Prometheus
    prometheus_enabled: bool = Field(default=True)
    prometheus_endpoint: str = Field(default="/metrics")
    prometheus_include_in_schema: bool = Field(default=False)
    prometheus_namespace: str = Field(default="python_api")
    prometheus_subsystem: str = Field(default="")

    # Redis
    redis_enabled: bool = Field(default=False)
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_pool_size: int = Field(default=10)
    redis_key_prefix: str = Field(default="api")

    # MinIO
    minio_enabled: bool = Field(default=False)
    minio_endpoint: str = Field(default="localhost:9000")
    minio_access_key: str | None = Field(
        default=None,
        description="MinIO access key (required if minio_enabled=True)",
    )
    minio_secret_key: SecretStr | None = Field(
        default=None,
        description="MinIO secret key (required if minio_enabled=True)",
    )
    minio_bucket: str = Field(default="uploads")
    minio_secure: bool = Field(default=False)

    # RabbitMQ
    rabbitmq_enabled: bool = Field(default=False)
    rabbitmq_host: str = Field(default="localhost")
    rabbitmq_port: int = Field(default=5672)
    rabbitmq_username: str | None = Field(
        default=None,
        description="RabbitMQ username (required if rabbitmq_enabled=True)",
    )
    rabbitmq_password: SecretStr | None = Field(
        default=None,
        description="RabbitMQ password (required if rabbitmq_enabled=True)",
    )
    rabbitmq_virtual_host: str = Field(default="/")

    # Keycloak
    keycloak_enabled: bool = Field(default=False)
    keycloak_server_url: str = Field(default="http://localhost:8080")
    keycloak_realm: str = Field(default="master")
    keycloak_client_id: str = Field(default="python-api")
    keycloak_client_secret: SecretStr | None = Field(
        default=None,
        description="Keycloak client secret (required if keycloak_enabled=True)",
    )

    @model_validator(mode="after")
    def validate_credentials(self) -> Self:
        """Validate that credentials are provided when services are enabled."""
        # MinIO validation
        if self.minio_enabled and (not self.minio_access_key or not self.minio_secret_key):
            msg = (
                "MinIO credentials required when minio_enabled=True. "
                "Set OBSERVABILITY__MINIO_ACCESS_KEY and OBSERVABILITY__MINIO_SECRET_KEY"
            )
            raise ValueError(msg)

        # RabbitMQ validation
        if self.rabbitmq_enabled and (not self.rabbitmq_username or not self.rabbitmq_password):
            msg = (
                "RabbitMQ credentials required when rabbitmq_enabled=True. "
                "Set OBSERVABILITY__RABBITMQ_USERNAME and OBSERVABILITY__RABBITMQ_PASSWORD"
            )
            raise ValueError(msg)

        # Keycloak validation
        if self.keycloak_enabled and not self.keycloak_client_secret:
            msg = (
                "Keycloak client secret required when keycloak_enabled=True. "
                "Set OBSERVABILITY__KEYCLOAK_CLIENT_SECRET"
            )
            raise ValueError(msg)

        return self
