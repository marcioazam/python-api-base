"""Correlation ID management for distributed tracing.

Provides context variable management for correlation IDs that propagate
through async call chains and appear in all log entries.

**Feature: observability-infrastructure**
**Requirement: R1 - Structured Logging Infrastructure**

Example:
    >>> from core.shared.logging.correlation import (
    ...     set_correlation_id,
    ...     get_correlation_id,
    ... )
    >>> set_correlation_id("abc-123")
    >>> get_correlation_id()
    'abc-123'
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Any

import structlog

# Context variable for correlation ID
_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def generate_correlation_id() -> str:
    """Generate a new correlation ID.

    Returns:
        UUID4 string

    Example:
        >>> cid = generate_correlation_id()
        >>> len(cid)
        36
    """
    return str(uuid.uuid4())


def get_correlation_id() -> str | None:
    """Get the current correlation ID from context.

    Returns:
        Current correlation ID or None if not set

    Example:
        >>> set_correlation_id("abc-123")
        >>> get_correlation_id()
        'abc-123'
    """
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set the correlation ID in context.

    Args:
        correlation_id: ID to set, or None to generate a new one

    Returns:
        The correlation ID that was set

    Example:
        >>> cid = set_correlation_id()  # Generates new ID
        >>> set_correlation_id("custom-id")  # Uses provided ID
        'custom-id'
    """
    if correlation_id is None:
        correlation_id = generate_correlation_id()

    _correlation_id_var.set(correlation_id)

    # Also bind to structlog context
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

    return correlation_id


def clear_correlation_id() -> None:
    """Clear the correlation ID from context.

    Example:
        >>> set_correlation_id("abc-123")
        >>> clear_correlation_id()
        >>> get_correlation_id() is None
        True
    """
    _correlation_id_var.set(None)
    structlog.contextvars.unbind_contextvars("correlation_id")


def bind_contextvars(**kwargs: Any) -> None:
    """Bind additional context variables to structlog.

    These will appear in all log entries until cleared.

    Args:
        **kwargs: Key-value pairs to bind

    Example:
        >>> bind_contextvars(user_id="123", tenant_id="acme")
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_contextvars() -> None:
    """Clear all bound context variables.

    Example:
        >>> bind_contextvars(user_id="123")
        >>> clear_contextvars()
    """
    structlog.contextvars.clear_contextvars()


def unbind_contextvars(*keys: str) -> None:
    """Unbind specific context variables.

    Args:
        *keys: Variable names to unbind

    Example:
        >>> bind_contextvars(user_id="123", tenant_id="acme")
        >>> unbind_contextvars("user_id")
    """
    structlog.contextvars.unbind_contextvars(*keys)
