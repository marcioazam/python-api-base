"""Auto-ban data models.

**Feature: file-size-compliance-phase2, Task 2.3**
**Validates: Requirements 1.3, 5.1, 5.2, 5.3**
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, UTC

from .enums import BanStatus, ViolationType


@dataclass(frozen=True, slots=True)
class Violation:
    """Record of a single violation."""

    identifier: str
    violation_type: ViolationType
    timestamp: datetime
    details: str = ""
    severity: int = 1


@dataclass
class BanRecord:
    """Record of a ban."""

    identifier: str
    reason: ViolationType
    banned_at: datetime
    expires_at: datetime | None
    violation_count: int
    status: BanStatus = BanStatus.ACTIVE

    @property
    def is_active(self) -> bool:
        """Check if ban is currently active.

        Uses timezone-aware datetime comparisons for correctness.
        Naive datetimes in expires_at are treated as UTC.
        """
        if self.status != BanStatus.ACTIVE:
            return False
        if self.expires_at is None:
            return True
        now = datetime.now(UTC)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return now < expires

    @property
    def is_permanent(self) -> bool:
        """Check if ban is permanent."""
        return self.expires_at is None


@dataclass
class BanThreshold:
    """Configuration for ban thresholds per violation type."""

    violation_type: ViolationType
    max_violations: int
    time_window: timedelta
    ban_duration: timedelta | None = None
    severity_multiplier: float = 1.0


@dataclass
class BanCheckResult:
    """Result of a ban check."""

    is_banned: bool
    ban_record: BanRecord | None = None
    reason: str = ""

    @classmethod
    def allowed(cls) -> "BanCheckResult":
        """Create allowed result."""
        return cls(is_banned=False)

    @classmethod
    def banned(cls, record: BanRecord, reason: str = "") -> "BanCheckResult":
        """Create banned result."""
        return cls(is_banned=True, ban_record=record, reason=reason)
