"""Security audit logger enums.

**Feature: full-codebase-review-2025, Task 1.4: Refactor audit_logger**
**Validates: Requirements 9.2**
"""

from enum import Enum


class SecurityEventType(str, Enum):
    """Types of security events."""

    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILURE = "AUTH_FAILURE"
    AUTHZ_DENIED = "AUTHZ_DENIED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SECRET_ACCESS = "SECRET_ACCESS"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
