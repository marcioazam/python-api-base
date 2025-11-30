"""Auto-ban detection service.

**Feature: file-size-compliance-phase2, Task 2.3**
**Feature: shared-modules-refactoring**
**Validates: Requirements 1.3, 2.1, 2.2, 5.1, 5.2, 5.3**
"""

from datetime import datetime, timedelta, UTC

from .config import AutoBanConfig, AutoBanConfigBuilder
from .enums import BanStatus, ViolationType
from .lock_manager import InMemoryLockManager, LockManager
from .models import BanCheckResult, BanRecord, BanThreshold, Violation
from .store import BanStore, InMemoryBanStore


class AutoBanService:
    """Service for automatic banning based on violations.

    Uses per-identifier locking to prevent race conditions when
    recording violations and checking ban status concurrently.
    """

    def __init__(
        self,
        config: AutoBanConfig,
        store: BanStore,
        lock_manager: LockManager | None = None,
    ) -> None:
        self._config = config
        self._store = store
        self._lock_manager = lock_manager or InMemoryLockManager()
        self._threshold_map: dict[ViolationType, BanThreshold] = {
            t.violation_type: t for t in config.thresholds
        }

    async def check_ban(self, identifier: str) -> BanCheckResult:
        """Check if identifier is currently banned.

        Uses per-identifier locking to ensure atomic check operations.
        """
        if identifier in self._config.allowlist:
            return BanCheckResult.allowed()

        async with self._lock_manager.acquire(identifier):
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
        """Record a violation and check if ban threshold is reached.

        Uses per-identifier locking to serialize concurrent violations
        and ensure atomic check-and-update operations.
        """
        if identifier in self._config.allowlist:
            return BanCheckResult.allowed()

        async with self._lock_manager.acquire(identifier):
            existing_ban = await self._store.get_ban(identifier)
            if existing_ban and existing_ban.is_active:
                return BanCheckResult.banned(existing_ban, "Already banned")

            violation = Violation(
                identifier=identifier,
                violation_type=violation_type,
                timestamp=datetime.now(UTC),
                details=details,
                severity=severity,
            )
            await self._store.add_violation(violation)

            threshold = self._threshold_map.get(violation_type)
            if not threshold:
                return BanCheckResult.allowed()

            since = datetime.now(UTC) - threshold.time_window
            violations = await self._store.get_violations(identifier, violation_type, since)

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

        base_duration = (
            threshold.ban_duration if threshold else self._config.default_ban_duration
        )

        now = datetime.now(UTC)

        if ban_count >= self._config.permanent_ban_after:
            expires_at = None
        elif self._config.escalation_enabled and base_duration:
            multiplier = self._config.escalation_multiplier ** (ban_count - 1)
            escalated = base_duration * multiplier
            if escalated > self._config.max_ban_duration:
                escalated = self._config.max_ban_duration
            expires_at = now + escalated
        elif base_duration:
            expires_at = now + base_duration
        else:
            expires_at = None

        ban = BanRecord(
            identifier=identifier,
            reason=reason,
            banned_at=now,
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
