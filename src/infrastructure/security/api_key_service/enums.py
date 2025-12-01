"""API Key enums.

**Feature: full-codebase-review-2025, Task 1.2: Refactor api_key_service**
**Validates: Requirements 9.2**
"""

from enum import Enum


class KeyStatus(str, Enum):
    """Status of an API key."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ROTATED = "rotated"


class KeyScope(str, Enum):
    """Scope/permission level for API keys."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    FULL = "full"
