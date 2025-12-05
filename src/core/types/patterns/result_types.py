"""Result pattern and callback type aliases using PEP 695 type statement.

**Feature: core-types-split-2025**

Note: Forward references are intentional for types defined in other modules.
"""
# ruff: noqa: F821

__all__ = [
    # Callbacks
    "AsyncCallback",
    # Specification
    "CompositeSpec",
    # Entity
    "EntityId",
    "EventCallback",
    # Result Pattern
    "Failure",
    "Middleware",
    "OperationResult",
    "Spec",
    "Success",
    "SyncCallback",
    "Timestamp",
    "VoidResult",
]

# =============================================================================
# Result Pattern Type Aliases
# =============================================================================

type Success[T] = "Ok[T]"
"""Type alias for successful result."""

type Failure[E] = "Err[E]"
"""Type alias for failed result."""

type OperationResult[T, E] = "Result[T, E]"
"""Type alias for operation result (success or failure)."""

type VoidResult[E] = "Result[None, E]"
"""Type alias for void operation result (no return value on success)."""

# =============================================================================
# Callback Type Aliases
# =============================================================================

type AsyncCallback[T] = "Callable[..., Awaitable[T]]"
"""Type alias for async callback function."""

type SyncCallback[T] = "Callable[..., T]"
"""Type alias for sync callback function."""

type EventCallback = "Callable[[DomainEvent], Awaitable[None] | None]"
"""Type alias for event handler callback."""

type Middleware = "Callable[[Request, Callable], Awaitable[Response]]"
"""Type alias for ASGI middleware callable."""

# =============================================================================
# Entity and ID Type Aliases
# =============================================================================

type EntityId = str | int
"""Type alias for entity identifier (ULID string or integer)."""

type Timestamp = "datetime"
"""Type alias for timestamp fields."""

# =============================================================================
# Specification Type Aliases
# =============================================================================

type Spec[T] = "Specification[T]"
"""Type alias for specification pattern."""

type CompositeSpec[T] = "Specification[T]"
"""Type alias for composite specification (AND/OR/NOT)."""
