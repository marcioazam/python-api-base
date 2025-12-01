"""Time source protocols for JWT service.

**Feature: full-codebase-review-2025, Task 1.3: Refactor jwt.py**
**Validates: Requirements 9.2, 11.1**
"""

from datetime import datetime, UTC
from typing import Protocol


class TimeSource(Protocol):
    """Protocol for injectable time sources.

    **Feature: core-code-review**
    **Validates: Requirements 11.1**
    """

    def now(self) -> datetime:
        """Get current UTC datetime."""
        ...


class SystemTimeSource:
    """Default system time source."""

    def now(self) -> datetime:
        """Get current UTC datetime from system clock."""
        return datetime.now(UTC)
