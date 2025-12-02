"""Unit tests for ScyllaDB configuration.

**Feature: observability-infrastructure**
**Requirement: R4 - Generic ScyllaDB Repository**
"""

import pytest

from infrastructure.scylladb.config import ScyllaDBConfig


class TestScyllaDBConfig:
    """Tests for ScyllaDBConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = ScyllaDBConfig()

        assert config.hosts == ["localhost"]
        assert config.port == 9042
        assert config.keyspace == "python_api_base"
        assert config.protocol_version == 4
        assert config.consistency_level == "LOCAL_QUORUM"

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = ScyllaDBConfig(
            hosts=["node1", "node2", "node3"],
            port=9043,
            keyspace="my_keyspace",
            username="admin",
            password="secret",
        )

        assert config.hosts == ["node1", "node2", "node3"]
        assert config.port == 9043
        assert config.keyspace == "my_keyspace"
        assert config.username == "admin"
        assert config.password == "secret"

    def test_to_cluster_kwargs_basic(self) -> None:
        """Test basic cluster kwargs generation."""
        pytest.importorskip("cassandra")

        config = ScyllaDBConfig(
            hosts=["localhost"],
            port=9042,
        )

        kwargs = config.to_cluster_kwargs()

        assert kwargs["contact_points"] == ["localhost"]
        assert kwargs["port"] == 9042
        assert "auth_provider" not in kwargs

    def test_ssl_config(self) -> None:
        """Test SSL configuration."""
        config = ScyllaDBConfig(
            ssl_enabled=True,
        )

        # Just verify the config is set correctly
        assert config.ssl_enabled is True
