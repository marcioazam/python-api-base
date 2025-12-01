"""Auto-ban storage backends.

**Feature: file-size-compliance-phase2, Task 2.3**
**Validates: Requirements 1.3, 5.1, 5.2, 5.3**
"""

from datetime import datetime
from typing import Protocol, runtime_checkable

from .enums import BanStatus, ViolationType
from .models import BanRecord, Violation


@runtime_checkable
class BanStore(Protocol):
    """Protocol for ban storage backends."""

    async def get_violations(
        self, identifier: str, violation_type: ViolationType, since: datetime
    ) -> list[Violation]: ...

    async def add_violation(self, violation: Violation) -> None: ...

    async def get_ban(self, identifier: str) -> BanRecord | None: ...

    async def set_ban(self, ban: BanRecord) -> None: ...

    async def remove_ban(self, identifier: str) -> bool: ...

    async def get_ban_count(self, identifier: str) -> int: ...

    async def increment_ban_count(self, identifier: str) -> int: ...


class InMemoryBanStore:
    """In-memory implementation of BanStore for testing."""

    def __init__(self) -> None:
        self._violations: dict[str, list[Violation]] = {}
        self._bans: dict[str, BanRecord] = {}
        self._ban_counts: dict[str, int] = {}

    async def get_violations(
        self, identifier: str, violation_type: ViolationType, since: datetime
    ) -> list[Violation]:
        """Get violations for identifier since timestamp."""
        violations = self._violations.get(identifier, [])
        return [
            v
            for v in violations
            if v.violation_type == violation_type and v.timestamp >= since
        ]

    async def add_violation(self, violation: Violation) -> None:
        """Add a violation record."""
        if violation.identifier not in self._violations:
            self._violations[violation.identifier] = []
        self._violations[violation.identifier].append(violation)

    async def get_ban(self, identifier: str) -> BanRecord | None:
        """Get active ban for identifier."""
        ban = self._bans.get(identifier)
        if ban and ban.is_active:
            return ban
        return None

    async def set_ban(self, ban: BanRecord) -> None:
        """Set a ban record."""
        self._bans[ban.identifier] = ban

    async def remove_ban(self, identifier: str) -> bool:
        """Remove a ban."""
        if identifier in self._bans:
            self._bans[identifier] = BanRecord(
                identifier=self._bans[identifier].identifier,
                reason=self._bans[identifier].reason,
                banned_at=self._bans[identifier].banned_at,
                expires_at=self._bans[identifier].expires_at,
                violation_count=self._bans[identifier].violation_count,
                status=BanStatus.LIFTED,
            )
            return True
        return False

    async def get_ban_count(self, identifier: str) -> int:
        """Get total ban count for identifier."""
        return self._ban_counts.get(identifier, 0)

    async def increment_ban_count(self, identifier: str) -> int:
        """Increment and return ban count."""
        self._ban_counts[identifier] = self._ban_counts.get(identifier, 0) + 1
        return self._ban_counts[identifier]
