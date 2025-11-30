"""Structured logging configuration with structlog."""

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.types import EventDict, Processor

# Context variable for request ID
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Get current request ID from context.
    
    Returns:
        Request ID or None if not set.
    """
    return request_id_ctx.get()


def set_request_id(request_id: str) -> None:
    """Set request ID in context.
    
    Args:
        request_id: Request ID to set.
    """
    request_id_ctx.set(request_id)


def clear_request_id() -> None:
    """Clear request ID from context."""
    request_id_ctx.set(None)


def add_request_id(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add request ID to log event.
    
    Args:
        logger: Logger instance.
        method_name: Logging method name.
        event_dict: Event dictionary.
        
    Returns:
        Updated event dictionary.
    """
    request_id = get_request_id()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def add_trace_context(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add OpenTelemetry trace context to log event.
    
    Adds trace_id and span_id from the current trace context for
    log correlation with distributed traces.
    
    **Feature: advanced-reusability**
    **Validates: Requirements 4.7**
    
    Args:
        logger: Logger instance.
        method_name: Logging method name.
        event_dict: Event dictionary.
        
    Returns:
        Updated event dictionary with trace context.
    """
    try:
        from my_api.infrastructure.observability.telemetry import (
            get_current_span_id,
            get_current_trace_id,
        )

        trace_id = get_current_trace_id()
        span_id = get_current_span_id()

        if trace_id:
            event_dict["trace_id"] = trace_id
        if span_id:
            event_dict["span_id"] = span_id
    except ImportError:
        pass

    return event_dict


# PII patterns to redact
PII_PATTERNS = {
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "credential",
    "credit_card",
    "ssn",
    "social_security",
}


def redact_pii(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Redact PII from log events.
    
    **Feature: infrastructure-code-review**
    **Validates: Requirements 5.1, 5.2**
    
    Args:
        logger: Logger instance.
        method_name: Logging method name.
        event_dict: Event dictionary.
        
    Returns:
        Event dictionary with PII redacted.
    """
    def _redact_value(key: str, value: Any) -> Any:
        """Redact value if key matches PII pattern."""
        # Handle None and non-string keys
        if value is None:
            return value

        key_lower = str(key).lower()
        for pattern in PII_PATTERNS:
            if pattern in key_lower:
                return "[REDACTED]"

        if isinstance(value, dict):
            return {k: _redact_value(k, v) for k, v in value.items()}
        elif isinstance(value, list):
            return [_redact_value(str(i), v) for i, v in enumerate(value)]
        elif isinstance(value, bytes):
            # Don't log raw bytes, could contain sensitive data
            return "[BINARY DATA]"

        return value

    return {k: _redact_value(k, v) for k, v in event_dict.items()}


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    development: bool = False,
    additional_pii_patterns: set[str] | None = None,
) -> None:
    """Configure structured logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Output format ("json" or "console").
        development: Enable development mode with pretty printing.
        additional_pii_patterns: Additional patterns to redact as PII.
        
    Raises:
        ValueError: If log_level is not a valid logging level.
    """
    # Validate log_level
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if log_level.upper() not in valid_levels:
        raise ValueError(
            f"Invalid log_level: {log_level}. "
            f"Must be one of: {', '.join(sorted(valid_levels))}"
        )

    # Add additional PII patterns if provided
    if additional_pii_patterns:
        PII_PATTERNS.update(additional_pii_patterns)
    # Shared processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_request_id,
        add_trace_context,  # Add trace_id and span_id for OTel correlation
        redact_pii,
    ]

    if development or log_format == "console":
        # Pretty console output for development
        processors: list[Processor] = [
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
        )
    else:
        # JSON output for production
        processors = [
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger.
    
    Args:
        name: Logger name (defaults to caller's module).
        
    Returns:
        Structured logger instance.
    """
    return structlog.get_logger(name)
