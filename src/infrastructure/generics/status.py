"""Standardized status enums for infrastructure modules.

**Feature: infrastructure-generics-review-2025**
**Validates: Requirements 4.1, 4.2, 4.4**

All enums use str mixin for JSON serialization compatibility.
"""

from enum import Enum


class BaseStatus(str, Enum):
    """Base status enum with common states.

    Used as foundation for domain-specific status enums.
    """

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConnectionStatus(str, Enum):
    """Connection pool status states."""

    IDLE = "idle"
    IN_USE = "in_use"
    UNHEALTHY = "unhealthy"
    CLOSED = "closed"


class TaskStatus(str, Enum):
    """Task execution status states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class HealthStatus(str, Enum):
    """Health check status states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class CacheStatus(str, Enum):
    """Cache entry status states."""

    VALID = "valid"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"


class MessageStatus(str, Enum):
    """Message processing status states."""

    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class AuthStatus(str, Enum):
    """Authentication status states."""

    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID = "invalid"
