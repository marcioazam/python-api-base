"""Unit tests for Kafka configuration.

**Feature: observability-infrastructure**
**Requirement: R3 - Generic Kafka Producer/Consumer**
"""

import pytest

from infrastructure.kafka.config import KafkaConfig


class TestKafkaConfig:
    """Tests for KafkaConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = KafkaConfig()

        assert config.bootstrap_servers == ["localhost:9092"]
        assert config.client_id == "python-api-base"
        assert config.group_id == "python-api-base-group"
        assert config.auto_offset_reset == "earliest"
        assert config.enable_auto_commit is True
        assert config.security_protocol == "PLAINTEXT"

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = KafkaConfig(
            bootstrap_servers=["kafka1:9092", "kafka2:9092"],
            client_id="my-app",
            group_id="my-group",
            auto_offset_reset="latest",
            enable_auto_commit=False,
        )

        assert config.bootstrap_servers == ["kafka1:9092", "kafka2:9092"]
        assert config.client_id == "my-app"
        assert config.group_id == "my-group"
        assert config.auto_offset_reset == "latest"
        assert config.enable_auto_commit is False

    def test_to_producer_config(self) -> None:
        """Test producer config generation."""
        config = KafkaConfig(
            bootstrap_servers=["kafka:9092"],
            client_id="producer-1",
            compression_type="gzip",
            linger_ms=10,
        )

        producer_config = config.to_producer_config()

        assert producer_config["bootstrap_servers"] == "kafka:9092"
        assert producer_config["client_id"] == "producer-1"
        assert producer_config["compression_type"] == "gzip"
        assert producer_config["linger_ms"] == 10

    def test_to_consumer_config(self) -> None:
        """Test consumer config generation."""
        config = KafkaConfig(
            bootstrap_servers=["kafka:9092"],
            client_id="consumer-1",
            group_id="test-group",
            auto_offset_reset="latest",
            enable_auto_commit=False,
        )

        consumer_config = config.to_consumer_config()

        assert consumer_config["bootstrap_servers"] == "kafka:9092"
        assert consumer_config["client_id"] == "consumer-1"
        assert consumer_config["group_id"] == "test-group"
        assert consumer_config["auto_offset_reset"] == "latest"
        assert consumer_config["enable_auto_commit"] is False

    def test_security_config_sasl(self) -> None:
        """Test SASL security configuration."""
        config = KafkaConfig(
            security_protocol="SASL_SSL",
            sasl_mechanism="PLAIN",
            sasl_username="user",
            sasl_password="pass",
        )

        producer_config = config.to_producer_config()

        assert producer_config["security_protocol"] == "SASL_SSL"
        assert producer_config["sasl_mechanism"] == "PLAIN"
        assert producer_config["sasl_plain_username"] == "user"
        assert producer_config["sasl_plain_password"] == "pass"

    def test_plaintext_no_security_config(self) -> None:
        """Test that PLAINTEXT doesn't add security config."""
        config = KafkaConfig(security_protocol="PLAINTEXT")

        producer_config = config.to_producer_config()

        assert "security_protocol" not in producer_config
        assert "sasl_mechanism" not in producer_config
