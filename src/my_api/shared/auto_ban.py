"""Auto-Ban System for automatic blocking after threshold violations.

This module provides an automatic ban system that tracks violations
and bans users/IPs after exceeding configurable thresholds.

**Feature: api-architecture-analysis, Property 10: Circuit Breaker State Machine**
**Validates: Requirements 5.4**
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol, runtime_checkable


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


@dataclass(frozen=True)
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
        """Check if ban is currently active."""
        if self.status != BanStatus.ACTIVE:
            return False
        if self.expires_at is None:
            return True
        return datetime.now() < self.expires_at

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
    ban_duration: timedelta | None = None  # None = permanent
    severity_multiplier: float = 1.0


@dataclass
class AutoBanConfig:
    """Configuration for the auto-ban system."""

    thresholds: list[BanThreshold] = field(default_factory=list)
    default_ban_duration: timedelta = field(default_factory=lambda: timedelta(hours=24))
    escalation_enabled: bool = True
    escalation_multiplier: float = 2.0
    max_ban_duration: timedelta = field(default_factory=lambda: timedelta(days=30))
    permanent_ban_after: int = 5  # Number of bans before permanent
    allowlist: set[str] = field(default_factory=set)

    @classmethod
    def default(cls) -> "AutoBanConfig":
        """Create default configuration."""
        return cls(
            thresholds=[
                BanThreshold(
                    violation_type=ViolationType.RATE_LIMIT,
                    max_violations=10,
                    time_window=timedelta(minutes=5),
                    ban_duration=timedelta(hours=1),
                ),
                BanThreshold(
                    violation_type=ViolationType.AUTH_FAILURE,
                    max_violations=5,
                    time_window=timedelta(minutes=15),
                    ban_duration=timedelta(hours=2),
                ),
                BanThreshold(
                    violation_type=ViolationType.BRUTE_FORCE,
                    max_violations=3,
                    time_window=timedelta(minutes=5),
                    ban_duration=timedelta(hours=24),
                ),
                BanThreshold(
                    violation_type=ViolationType.SUSPICIOUS_ACTIVITY,
                    max_violations=5,
                    time_window=timedelta(hours=1),
                    ban_duration=timedelta(hours=12),
                ),
                BanThreshold(
                    violation_type=ViolationType.SPAM,
                    max_violations=3,
                    time_window=timedelta(minutes=10),
                    ban_duration=timedelta(hours=6),
                ),
                BanThreshold(
                    violation_type=ViolationType.ABUSE,
                    max_violations=2,
                    time_window=timedelta(hours=1),
                    ban_duration=timedelta(days=7),
                ),
            ]
        )


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


class AutoBanService:
    """Service for automatic banning based on violations.

    Tracks violations and automatically bans identifiers (users/IPs)
    when they exceed configured thresholds.
    """

    def __init__(self, config: AutoBanConfig, store: BanStore) -> None:
        self._config = config
        self._store = store
        self._threshold_map: dict[ViolationType, BanThreshold] = {
            t.violation_type: t for t in config.thresholds
        }

    async def check_ban(self, identifier: str) -> BanCheckResult:
        """Check if identifier is currently banned."""
        if identifier in self._config.allowlist:
            return BanCheckResult.allowed()

        ban = await self._store.get_ban(identifier)
        if ban and ban.is_active:
            return BanCheckResult.banned(
                ban, f"Banned for {ban.reason.value} until {ban.expires_at}"
            )
        return BanCheckResult.allowed()

    async def record_violation(
        self,
        identifier: str,
        violation_type: ViolationType,
        details: str = "",
        severity: int = 1,
    ) -> BanCheckResult:
        """Record a violation and check if ban threshold is reached."""
        if identifier in self._config.allowlist:
            return BanCheckResult.allowed()

        # Check if already banned
        existing_ban = await self._store.get_ban(identifier)
        if existing_ban and existing_ban.is_active:
            return BanCheckResult.banned(existing_ban, "Already banned")

        # Record the violation
        violation = Violation(
            identifier=identifier,
            violation_type=violation_type,
            timestamp=datetime.now(),
            details=details,
            severity=severity,
        )
        await self._store.add_violation(violation)

        # Check threshold
        threshold = self._threshold_map.get(violation_type)
        if not threshold:
            return BanCheckResult.allowed()

        since = datetime.now() - threshold.time_window
        violations = await self._store.get_violations(identifier, violation_type, since)

        # Calculate effective count with severity
        effective_count = sum(v.severity * threshold.severity_multiplier for v in violations)

        if effective_count >= threshold.max_violations:
            ban = await self._create_ban(identifier, violation_type, len(violations))
            return BanCheckResult.banned(ban, f"Threshold exceeded for {violation_type.value}")

        return BanCheckResult.allowed()

    async def _create_ban(
        self, identifier: str, reason: ViolationType, violation_count: int
    ) -> BanRecord:
        """Create a ban record with escalation logic."""
        ban_count = await self._store.increment_ban_count(identifier)
        threshold = self._threshold_map.get(reason)

        # Calculate ban duration with escalation
        base_duration = (
            threshold.ban_duration if threshold else self._config.default_ban_duration
        )

        if ban_count >= self._config.permanent_ban_after:
            expires_at = None  # Permanent ban
        elif self._config.escalation_enabled and base_duration:
            multiplier = self._config.escalation_multiplier ** (ban_count - 1)
            escalated = base_duration * multiplier
            if escalated > self._config.max_ban_duration:
                escalated = self._config.max_ban_duration
            expires_at = datetime.now() + escalated
        elif base_duration:
            expires_at = datetime.now() + base_duration
        else:
            expires_at = None

        ban = BanRecord(
            identifier=identifier,
            reason=reason,
            banned_at=datetime.now(),
            expires_at=expires_at,
            violation_count=violation_count,
            status=BanStatus.ACTIVE,
        )
        await self._store.set_ban(ban)
        return ban

    async def lift_ban(self, identifier: str) -> bool:
        """Manually lift a ban."""
        return await self._store.remove_ban(identifier)

    async def is_banned(self, identifier: str) -> bool:
        """Quick check if identifier is banned."""
        result = await self.check_ban(identifier)
        return result.is_banned


class AutoBanConfigBuilder:
    """Fluent builder for AutoBanConfig."""

    def __init__(self) -> None:
        self._thresholds: list[BanThreshold] = []
        self._default_ban_duration = timedelta(hours=24)
        self._escalation_enabled = True
        self._escalation_multiplier = 2.0
        self._max_ban_duration = timedelta(days=30)
        self._permanent_ban_after = 5
        self._allowlist: set[str] = set()

    def add_threshold(
        self,
        violation_type: ViolationType,
        max_violations: int,
        time_window: timedelta,
        ban_duration: timedelta | None = None,
        severity_multiplier: float = 1.0,
    ) -> "AutoBanConfigBuilder":
        """Add a threshold configuration."""
        self._thresholds.append(
            BanThreshold(
                violation_type=violation_type,
                max_violations=max_violations,
                time_window=time_window,
                ban_duration=ban_duration,
                severity_multiplier=severity_multiplier,
            )
        )
        return self

    def with_default_ban_duration(self, duration: timedelta) -> "AutoBanConfigBuilder":
        """Set default ban duration."""
        self._default_ban_duration = duration
        return self

    def with_escalation(
        self, enabled: bool = True, multiplier: float = 2.0
    ) -> "AutoBanConfigBuilder":
        """Configure escalation settings."""
        self._escalation_enabled = enabled
        self._escalation_multiplier = multiplier
        return self

    def with_max_ban_duration(self, duration: timedelta) -> "AutoBanConfigBuilder":
        """Set maximum ban duration."""
        self._max_ban_duration = duration
        return self

    def with_permanent_ban_after(self, count: int) -> "AutoBanConfigBuilder":
        """Set number of bans before permanent."""
        self._permanent_ban_after = count
        return self

    def with_allowlist(self, identifiers: set[str]) -> "AutoBanConfigBuilder":
        """Set allowlist of identifiers that cannot be banned."""
        self._allowlist = identifiers
        return self

    def add_to_allowlist(self, identifier: str) -> "AutoBanConfigBuilder":
        """Add identifier to allowlist."""
        self._allowlist.add(identifier)
        return self

    def build(self) -> AutoBanConfig:
        """Build the configuration."""
        return AutoBanConfig(
            thresholds=self._thresholds,
            default_ban_duration=self._default_ban_duration,
            escalation_enabled=self._escalation_enabled,
            escalation_multiplier=self._escalation_multiplier,
            max_ban_duration=self._max_ban_duration,
            permanent_ban_after=self._permanent_ban_after,
            allowlist=self._allowlist,
        )


# Convenience factory functions
def create_auto_ban_service(
    config: AutoBanConfig | None = None,
    store: BanStore | None = None,
) -> AutoBanService:
    """Create an AutoBanService with defaults."""
    return AutoBanService(
        config=config or AutoBanConfig.default(),
        store=store or InMemoryBanStore(),
    )


def create_strict_config() -> AutoBanConfig:
    """Create a strict configuration with lower thresholds."""
    return (
        AutoBanConfigBuilder()
        .add_threshold(ViolationType.RATE_LIMIT, 5, timedelta(minutes=5), timedelta(hours=2))
        .add_threshold(ViolationType.AUTH_FAILURE, 3, timedelta(minutes=10), timedelta(hours=4))
        .add_threshold(ViolationType.BRUTE_FORCE, 2, timedelta(minutes=5), timedelta(days=1))
        .add_threshold(ViolationType.SUSPICIOUS_ACTIVITY, 3, timedelta(hours=1), timedelta(days=1))
        .add_threshold(ViolationType.SPAM, 2, timedelta(minutes=10), timedelta(hours=12))
        .add_threshold(ViolationType.ABUSE, 1, timedelta(hours=1), timedelta(days=14))
        .with_permanent_ban_after(3)
        .build()
    )


def create_lenient_config() -> AutoBanConfig:
    """Create a lenient configuration with higher thresholds."""
    return (
        AutoBanConfigBuilder()
        .add_threshold(ViolationType.RATE_LIMIT, 20, timedelta(minutes=10), timedelta(minutes=30))
        .add_threshold(ViolationType.AUTH_FAILURE, 10, timedelta(minutes=30), timedelta(hours=1))
        .add_threshold(ViolationType.BRUTE_FORCE, 5, timedelta(minutes=10), timedelta(hours=6))
        .add_threshold(ViolationType.SUSPICIOUS_ACTIVITY, 10, timedelta(hours=2), timedelta(hours=6))
        .add_threshold(ViolationType.SPAM, 5, timedelta(minutes=15), timedelta(hours=3))
        .add_threshold(ViolationType.ABUSE, 3, timedelta(hours=2), timedelta(days=3))
        .with_permanent_ban_after(10)
        .with_escalation(enabled=False)
        .build()
    )
