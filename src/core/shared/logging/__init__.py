"""Structured logging infrastructure with ECS compatibility.

Provides:
- Structlog configuration with JSON output
- Correlation ID propagation
- PII redaction
- Elasticsearch transport

**Feature: observability-infrastructure**
**Requirement: R1 - Structured Logging Infrastructure**
"""

from core.shared.logging.config import (
    configure_logging,
    get_logger,
    LogLevel,
)
from core.shared.logging.correlation import (
    get_correlation_id,
    set_correlation_id,
    bind_contextvars,
    clear_contextvars,
)
from core.shared.logging.redaction import (
    RedactionProcessor,
    PII_PATTERNS,
)

__all__ = [
    # Config
    "configure_logging",
    "get_logger",
    "LogLevel",
    # Correlation
    "get_correlation_id",
    "set_correlation_id",
    "bind_contextvars",
    "clear_contextvars",
    # Redaction
    "RedactionProcessor",
    "PII_PATTERNS",
]
