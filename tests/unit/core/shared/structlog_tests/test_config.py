"""Unit tests for logging configuration.

**Feature: observability-infrastructure**
**Requirement: R1.1 - Structlog Configuration**
"""

import pytest
import structlog

from core.shared.logging.config import (
    configure_logging,
    get_logger,
    LogLevel,
)


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_with_defaults(self) -> None:
        """Test configuration with default settings."""
        configure_logging()

        logger = get_logger("test")
        assert logger is not None

    def test_configure_json_output(self) -> None:
        """Test configuration with JSON output."""
        configure_logging(json_output=True)

        logger = get_logger("test")
        assert logger is not None

    def test_configure_console_output(self) -> None:
        """Test configuration with console output."""
        configure_logging(json_output=False)

        logger = get_logger("test")
        assert logger is not None

    def test_configure_log_level_string(self) -> None:
        """Test configuration with string log level."""
        configure_logging(log_level="DEBUG")

        logger = get_logger("test")
        assert logger is not None

    def test_configure_log_level_enum(self) -> None:
        """Test configuration with enum log level."""
        configure_logging(log_level=LogLevel.WARNING)

        logger = get_logger("test")
        assert logger is not None

    def test_configure_service_info(self) -> None:
        """Test configuration with service info."""
        configure_logging(
            service_name="test-service",
            service_version="1.0.0",
            environment="testing",
        )

        logger = get_logger("test")
        assert logger is not None

    def test_configure_ecs_fields(self) -> None:
        """Test configuration with ECS field mapping."""
        configure_logging(add_ecs_fields=True)

        logger = get_logger("test")
        assert logger is not None

    def test_configure_without_ecs_fields(self) -> None:
        """Test configuration without ECS field mapping."""
        configure_logging(add_ecs_fields=False)

        logger = get_logger("test")
        assert logger is not None


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_with_name(self) -> None:
        """Test getting logger with specific name."""
        configure_logging()

        logger = get_logger("my_module")

        assert logger is not None

    def test_get_logger_without_name(self) -> None:
        """Test getting logger without name."""
        configure_logging()

        logger = get_logger()

        assert logger is not None

    def test_logger_has_log_methods(self) -> None:
        """Test that logger has standard log methods."""
        configure_logging()
        logger = get_logger("test")

        assert hasattr(logger, "debug")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "critical")


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_log_level_values(self) -> None:
        """Test LogLevel enum values."""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.CRITICAL == "CRITICAL"

    def test_log_level_from_string(self) -> None:
        """Test creating LogLevel from string."""
        level = LogLevel("INFO")
        assert level == LogLevel.INFO

    def test_log_level_uppercase(self) -> None:
        """Test LogLevel handles case."""
        level = LogLevel("DEBUG")
        assert level == LogLevel.DEBUG
