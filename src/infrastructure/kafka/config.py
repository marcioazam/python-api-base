"""Kafka configuration.

**Feature: observability-infrastructure**
**Requirement: R3 - Generic Kafka Producer/Consumer**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class KafkaConfig:
    """Configuration for Kafka client.

    Attributes:
        bootstrap_servers: List of Kafka brokers
        client_id: Client identifier
        group_id: Consumer group ID
        auto_offset_reset: Where to start consuming (earliest, latest)
        enable_auto_commit: Whether to auto commit offsets
        security_protocol: Security protocol (PLAINTEXT, SSL, SASL_SSL)
        sasl_mechanism: SASL mechanism (PLAIN, SCRAM-SHA-256, etc.)
        sasl_username: SASL username
        sasl_password: SASL password
        ssl_context: SSL context for secure connections
        request_timeout_ms: Request timeout in milliseconds
        max_batch_size: Maximum batch size for producer
        linger_ms: Producer linger time in milliseconds
        compression_type: Compression (none, gzip, snappy, lz4, zstd)
    """

    bootstrap_servers: list[str] = field(
        default_factory=lambda: ["localhost:9092"]
    )
    client_id: str = "python-api-base"
    group_id: str = "python-api-base-group"
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = True
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: str | None = None
    sasl_username: str | None = None
    sasl_password: str | None = None
    ssl_context: Any | None = None
    request_timeout_ms: int = 30000
    max_batch_size: int = 16384
    linger_ms: int = 0
    compression_type: str = "none"

    def to_producer_config(self) -> dict[str, Any]:
        """Convert to aiokafka producer config.

        Returns:
            Producer configuration dict
        """
        config: dict[str, Any] = {
            "bootstrap_servers": ",".join(self.bootstrap_servers),
            "client_id": self.client_id,
            "request_timeout_ms": self.request_timeout_ms,
            "max_batch_size": self.max_batch_size,
            "linger_ms": self.linger_ms,
            "compression_type": self.compression_type,
        }

        self._add_security_config(config)
        return config

    def to_consumer_config(self) -> dict[str, Any]:
        """Convert to aiokafka consumer config.

        Returns:
            Consumer configuration dict
        """
        config: dict[str, Any] = {
            "bootstrap_servers": ",".join(self.bootstrap_servers),
            "client_id": self.client_id,
            "group_id": self.group_id,
            "auto_offset_reset": self.auto_offset_reset,
            "enable_auto_commit": self.enable_auto_commit,
            "request_timeout_ms": self.request_timeout_ms,
        }

        self._add_security_config(config)
        return config

    def _add_security_config(self, config: dict[str, Any]) -> None:
        """Add security configuration to config dict."""
        if self.security_protocol != "PLAINTEXT":
            config["security_protocol"] = self.security_protocol

            if self.sasl_mechanism:
                config["sasl_mechanism"] = self.sasl_mechanism
                config["sasl_plain_username"] = self.sasl_username
                config["sasl_plain_password"] = self.sasl_password

            if self.ssl_context:
                config["ssl_context"] = self.ssl_context
