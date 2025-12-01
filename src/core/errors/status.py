"""Centralized status codes and enums.

**Feature: 2025-generics-clean-code-review**
**Validates: Requirements 10.2**
"""

from enum import Enum


class OperationStatus(str, Enum):
    """Status codes for operations."""

    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    PARTIAL = "partial"


class ValidationStatus(str, Enum):
    """Status codes for validation results."""

    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    SKIPPED = "skipped"


class EntityStatus(str, Enum):
    """Common entity status values."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    DELETED = "deleted"
    ARCHIVED = "archived"


class UserStatus(str, Enum):
    """User-specific status values."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_VERIFICATION = "pending_verification"
    SUSPENDED = "suspended"
    BANNED = "banned"
    DELETED = "deleted"


class TaskStatus(str, Enum):
    """Task/Job status values."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


# Re-export from constants for backward compatibility
