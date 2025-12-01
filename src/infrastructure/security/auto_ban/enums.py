"""Auto-ban enums for violation types and ban status.

**Feature: file-size-compliance-phase2, Task 2.3**
**Validates: Requirements 1.3, 5.1, 5.2, 5.3**
"""

from enum import Enum


class ViolationType(Enum):
    """Types of violations that can trigger a ban."""

    RATE_LIMIT = "rate_limit"
    AUTH_FAILURE = "auth_failure"
    INVALID_INPUT = "invalid_input"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    BRUTE_FORCE = "brute_force"
    SPAM = "spam"
    ABUSE = "abuse"


class BanStatus(Enum):
    """Status of a ban."""

    ACTIVE = "active"
    EXPIRED = "expired"
    LIFTED = "lifted"
