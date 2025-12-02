"""Structured logging configuration with ECS compatibility.

Configures structlog with:
- JSON output format
- ECS-compatible field names
- Correlation ID support
- PII redaction
- Elasticsearch transport (optional)

**Feature: observability-infrastructure**
**Requirement: R1 - Structured Logging Infrastructure**

Example:
    >>> from core.shared.logging import configure_logging, get_logger
    >>> configure_logging(log_level="INFO", json_output=True)
    >>> logger = get_logger("my_service")
    >>> logger.info("User logged in", user_id="123")
"""

from __future__ import annotations

import logging
import sys
from enum import StrEnum
from typing import TYPE_CHECKING, Any

import structlog
from structlog.types import Processor

if TYPE_CHECKING:
    from collections.abc import Sequence


class LogLevel(StrEnum):
    """Log level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ECS field mapping for Elasticsearch compatibility
ECS_FIELD_MAP = {
    "timestamp": "@timestamp",
    "level": "log.level",
    "logger": "log.logger",
    "event": "message",
    "correlation_id": "trace.id",
    "service_name": "service.name",
    "service_version": "service.version",
    "environment": "service.environment",
}


def _add_ecs_fields(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add ECS-compatible fields to log event."""
    # Rename fields to ECS format
    for old_key, new_key in ECS_FIELD_MAP.items():
        if old_key in event_dict:
            event_dict[new_key] = event_dict.pop(old_key)

    # Add ECS version
    event_dict["ecs.version"] = "8.11"

    return event_dict


def _add_service_info(
    service_name: str,
    service_version: str,
    environment: str,
) -> Processor:
    """Create processor that adds service info to all logs."""

    def processor(
        logger: logging.Logger,
        method_name: str,
        event_dict: dict[str, Any],
    ) -> dict[str, Any]:
        event_dict["service_name"] = service_name
        event_dict["service_version"] = service_version
        event_dict["environment"] = environment
        return event_dict

    return processor


def _get_processors(
    json_output: bool,
    add_ecs_fields: bool,
    service_name: str,
    service_version: str,
    environment: str,
    extra_processors: Sequence[Processor] | None = None,
) -> list[Processor]:
    """Build processor chain for structlog."""
    from core.shared.logging.redaction import RedactionProcessor

    processors: list[Processor] = [
        # Add context variables (correlation_id, etc.)
        structlog.contextvars.merge_contextvars,
        # Add log level
        structlog.processors.add_log_level,
        # Add timestamp (ISO format, UTC)
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Add service info
        _add_service_info(service_name, service_version, environment),
        # PII redaction
        RedactionProcessor(),
        # Stack info for exceptions
        structlog.processors.StackInfoRenderer(),
        # Format exception info
        structlog.processors.format_exc_info,
        # Unicode decoder
        structlog.processors.UnicodeDecoder(),
    ]

    # Add extra processors if provided
    if extra_processors:
        processors.extend(extra_processors)

    # Add ECS field mapping if enabled
    if add_ecs_fields:
        processors.append(_add_ecs_fields)

    # Final renderer
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    return processors


def configure_logging(
    log_level: str | LogLevel = LogLevel.INFO,
    json_output: bool = True,
    add_ecs_fields: bool = True,
    service_name: str = "python-api-base",
    service_version: str = "1.0.0",
    environment: str = "development",
    extra_processors: Sequence[Processor] | None = None,
) -> None:
    """Configure structlog with ECS-compatible processors.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: If True, output JSON; otherwise, use console renderer
        add_ecs_fields: If True, rename fields to ECS format
        service_name: Service name for log context
        service_version: Service version for log context
        environment: Environment (development, staging, production)
        extra_processors: Additional structlog processors

    Example:
        >>> configure_logging(
        ...     log_level="INFO",
        ...     json_output=True,
        ...     service_name="my-api",
        ... )
    """
    # Convert string to LogLevel if needed
    if isinstance(log_level, str):
        log_level = LogLevel(log_level.upper())

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.value),
    )

    # Build processor chain
    processors = _get_processors(
        json_output=json_output,
        add_ecs_fields=add_ecs_fields,
        service_name=service_name,
        service_version=service_version,
        environment=environment,
        extra_processors=extra_processors,
    )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.value)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get a configured structlog logger.

    Args:
        name: Logger name (defaults to calling module)

    Returns:
        Configured structlog BoundLogger

    Example:
        >>> logger = get_logger("my_module")
        >>> logger.info("Processing started", item_count=42)
    """
    return structlog.get_logger(name)
