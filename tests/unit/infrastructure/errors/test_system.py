"""Tests for system errors module.

Tests for TelemetryError and ConfigurationError.
"""

import pytest

from infrastructure.errors.base import InfrastructureError
from infrastructure.errors.system import (
    ConfigurationError,
    TelemetryError,
)


class TestTelemetryError:
    """Tests for TelemetryError class."""

    def test_is_infrastructure_error(self) -> None:
        """TelemetryError should be an InfrastructureError."""
        error = TelemetryError("test")
        assert isinstance(error, InfrastructureError)

    def test_init_with_message(self) -> None:
        """Error should store message."""
        error = TelemetryError("metrics export failed")
        assert error.message == "metrics export failed"

    def test_init_with_details(self) -> None:
        """Error should store details."""
        error = TelemetryError("export failed", {"endpoint": "otel:4317"})
        assert error.details == {"endpoint": "otel:4317"}

    def test_init_default_details(self) -> None:
        """Error should have empty dict details by default."""
        error = TelemetryError("test")
        assert error.details == {}

    def test_can_be_raised(self) -> None:
        """TelemetryError can be raised and caught."""
        with pytest.raises(TelemetryError):
            raise TelemetryError("test")

    def test_can_be_caught_as_infrastructure_error(self) -> None:
        """TelemetryError can be caught as InfrastructureError."""
        with pytest.raises(InfrastructureError):
            raise TelemetryError("test")

    def test_metric_collection_failure(self) -> None:
        """Test metric collection failure scenario."""
        error = TelemetryError(
            "Failed to collect metrics",
            {"collector": "prometheus", "reason": "timeout"},
        )
        assert error.details["collector"] == "prometheus"

    def test_trace_export_failure(self) -> None:
        """Test trace export failure scenario."""
        error = TelemetryError(
            "Trace export failed",
            {"exporter": "jaeger", "spans_dropped": 100},
        )
        assert error.details["spans_dropped"] == 100


class TestConfigurationError:
    """Tests for ConfigurationError class."""

    def test_is_infrastructure_error(self) -> None:
        """ConfigurationError should be an InfrastructureError."""
        error = ConfigurationError("test")
        assert isinstance(error, InfrastructureError)

    def test_init_with_message(self) -> None:
        """Error should store message."""
        error = ConfigurationError("missing required config")
        assert error.message == "missing required config"

    def test_init_with_details(self) -> None:
        """Error should store details."""
        error = ConfigurationError("invalid", {"key": "DATABASE_URL"})
        assert error.details == {"key": "DATABASE_URL"}

    def test_init_default_details(self) -> None:
        """Error should have empty dict details by default."""
        error = ConfigurationError("test")
        assert error.details == {}

    def test_can_be_raised(self) -> None:
        """ConfigurationError can be raised and caught."""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("test")

    def test_can_be_caught_as_infrastructure_error(self) -> None:
        """ConfigurationError can be caught as InfrastructureError."""
        with pytest.raises(InfrastructureError):
            raise ConfigurationError("test")

    def test_missing_config_scenario(self) -> None:
        """Test missing configuration error."""
        error = ConfigurationError(
            "Required configuration missing",
            {"missing_keys": ["API_KEY", "SECRET"]},
        )
        assert "API_KEY" in error.details["missing_keys"]

    def test_invalid_config_value_scenario(self) -> None:
        """Test invalid configuration value error."""
        error = ConfigurationError(
            "Invalid configuration value",
            {"key": "LOG_LEVEL", "value": "INVALID", "allowed": ["DEBUG", "INFO"]},
        )
        assert error.details["key"] == "LOG_LEVEL"

    def test_config_parse_error_scenario(self) -> None:
        """Test configuration parse error."""
        error = ConfigurationError(
            "Failed to parse configuration file",
            {"file": "config.yaml", "line": 42},
        )
        assert error.details["line"] == 42
