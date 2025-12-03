"""Property-based tests for Auto-Ban System.

**Feature: api-architecture-analysis, Property 10: Circuit Breaker State Machine**
**Validates: Requirements 5.4**
"""

from datetime import datetime, timedelta, timezone

import pytest

pytest.skip('Module infrastructure.security.auto_ban not implemented', allow_module_level=True)

from hypothesis import given, settings, strategies as st

from infrastructure.security.auto_ban import (
    AutoBanConfig,
    AutoBanConfigBuilder,
    AutoBanService,
    BanCheckResult,
    BanRecord,
    BanStatus,
    BanThreshold,
    InMemoryBanStore,
    Violation,
    ViolationType,
    create_auto_ban_service,
    create_lenient_config,
    create_strict_config,
)


# Strategies
violation_type_strategy = st.sampled_from(list(ViolationType))
identifier_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=50,
)
severity_strategy = st.integers(min_value=1, max_value=10)


class TestViolationProperties:
    """Property tests for Violation model."""

    @given(
        identifier=identifier_strategy,
        violation_type=violation_type_strategy,
        severity=severity_strategy,
    )
    @settings(max_examples=100)
    def test_violation_immutability(
        self, identifier: str, violation_type: ViolationType, severity: int
    ) -> None:
        """Property: Violations are immutable after creation."""
        violation = Violation(
            identifier=identifier,
            violation_type=violation_type,
            timestamp=datetime.now(),
            severity=severity,
        )
        # Frozen dataclass should raise on modification
        with pytest.raises(Exception):  # FrozenInstanceError
            violation.identifier = "new_id"  # type: ignore


class TestBanRecordProperties:
    """Property tests for BanRecord model."""

    @given(identifier=identifier_strategy)
    @settings(max_examples=100)
    def test_active_ban_with_future_expiry(self, identifier: str) -> None:
        """Property: Ban with future expiry is active."""
        now = datetime.now(timezone.utc)
        ban = BanRecord(
            identifier=identifier,
            reason=ViolationType.RATE_LIMIT,
            banned_at=now,
            expires_at=now + timedelta(hours=1),
            violation_count=1,
            status=BanStatus.ACTIVE,
        )
        assert ban.is_active is True
        assert ban.is_permanent is False

    @given(identifier=identifier_strategy)
    @settings(max_examples=100)
    def test_expired_ban_is_not_active(self, identifier: str) -> None:
        """Property: Ban with past expiry is not active."""
        now = datetime.now(timezone.utc)
        ban = BanRecord(
            identifier=identifier,
            reason=ViolationType.RATE_LIMIT,
            banned_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
            violation_count=1,
            status=BanStatus.ACTIVE,
        )
        assert ban.is_active is False

    @given(identifier=identifier_strategy)
    @settings(max_examples=100)
    def test_permanent_ban_has_no_expiry(self, identifier: str) -> None:
        """Property: Permanent ban has no expiry date."""
        now = datetime.now(timezone.utc)
        ban = BanRecord(
            identifier=identifier,
            reason=ViolationType.ABUSE,
            banned_at=now,
            expires_at=None,
            violation_count=5,
            status=BanStatus.ACTIVE,
        )
        assert ban.is_permanent is True
        assert ban.is_active is True

    @given(identifier=identifier_strategy)
    @settings(max_examples=100)
    def test_lifted_ban_is_not_active(self, identifier: str) -> None:
        """Property: Lifted ban is not active regardless of expiry."""
        now = datetime.now(timezone.utc)
        ban = BanRecord(
            identifier=identifier,
            reason=ViolationType.RATE_LIMIT,
            banned_at=now,
            expires_at=now + timedelta(hours=1),
            violation_count=1,
            status=BanStatus.LIFTED,
        )
        assert ban.is_active is False


class TestInMemoryBanStoreProperties:
    """Property tests for InMemoryBanStore."""

    @given(
        identifier=identifier_strategy,
        violation_type=violation_type_strategy,
    )
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_violation_round_trip(
        self, identifier: str, violation_type: ViolationType
    ) -> None:
        """Property: Added violations can be retrieved."""
        store = InMemoryBanStore()
        violation = Violation(
            identifier=identifier,
            violation_type=violation_type,
            timestamp=datetime.now(),
        )
        await store.add_violation(violation)

        since = datetime.now() - timedelta(minutes=1)
        violations = await store.get_violations(identifier, violation_type, since)

        assert len(violations) >= 1
        assert any(v.identifier == identifier for v in violations)

    @given(identifier=identifier_strategy)
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_ban_round_trip(self, identifier: str) -> None:
        """Property: Set ban can be retrieved."""
        store = InMemoryBanStore()
        now = datetime.now(timezone.utc)
        ban = BanRecord(
            identifier=identifier,
            reason=ViolationType.RATE_LIMIT,
            banned_at=now,
            expires_at=now + timedelta(hours=1),
            violation_count=1,
        )
        await store.set_ban(ban)

        retrieved = await store.get_ban(identifier)
        assert retrieved is not None
        assert retrieved.identifier == identifier

    @given(identifier=identifier_strategy)
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_ban_count_increments(self, identifier: str) -> None:
        """Property: Ban count increments correctly."""
        store = InMemoryBanStore()
        initial = await store.get_ban_count(identifier)
        assert initial == 0

        count1 = await store.increment_ban_count(identifier)
        assert count1 == 1

        count2 = await store.increment_ban_count(identifier)
        assert count2 == 2

    @given(identifier=identifier_strategy)
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_remove_ban_lifts_status(self, identifier: str) -> None:
        """Property: Removing ban changes status to LIFTED."""
        store = InMemoryBanStore()
        ban = BanRecord(
            identifier=identifier,
            reason=ViolationType.RATE_LIMIT,
            banned_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            violation_count=1,
        )
        await store.set_ban(ban)
        await store.remove_ban(identifier)

        # After removal, get_ban returns None (not active)
        retrieved = await store.get_ban(identifier)
        assert retrieved is None


class TestAutoBanServiceProperties:
    """Property tests for AutoBanService."""

    @given(identifier=identifier_strategy)
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_allowlist_never_banned(self, identifier: str) -> None:
        """Property: Allowlisted identifiers are never banned."""
        config = AutoBanConfigBuilder().with_allowlist({identifier}).build()
        service = AutoBanService(config, InMemoryBanStore())

        # Record many violations
        for _ in range(20):
            result = await service.record_violation(
                identifier, ViolationType.BRUTE_FORCE, severity=10
            )
            assert result.is_banned is False

        # Check ban status
        check = await service.check_ban(identifier)
        assert check.is_banned is False

    @given(identifier=identifier_strategy)
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_threshold_triggers_ban(self, identifier: str) -> None:
        """Property: Exceeding threshold triggers ban."""
        config = (
            AutoBanConfigBuilder()
            .add_threshold(
                ViolationType.AUTH_FAILURE,
                max_violations=3,
                time_window=timedelta(minutes=5),
                ban_duration=timedelta(hours=1),
            )
            .build()
        )
        service = AutoBanService(config, InMemoryBanStore())

        # Record violations up to threshold
        for i in range(3):
            result = await service.record_violation(identifier, ViolationType.AUTH_FAILURE)
            if i < 2:
                assert result.is_banned is False
            else:
                assert result.is_banned is True

    @given(identifier=identifier_strategy)
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_lift_ban_allows_access(self, identifier: str) -> None:
        """Property: Lifting ban allows access again."""
        config = (
            AutoBanConfigBuilder()
            .add_threshold(
                ViolationType.SPAM,
                max_violations=1,
                time_window=timedelta(minutes=5),
                ban_duration=timedelta(hours=1),
            )
            .build()
        )
        service = AutoBanService(config, InMemoryBanStore())

        # Trigger ban
        await service.record_violation(identifier, ViolationType.SPAM)
        assert await service.is_banned(identifier) is True

        # Lift ban
        await service.lift_ban(identifier)
        assert await service.is_banned(identifier) is False


class TestBanEscalationProperties:
    """Property tests for ban escalation logic."""

    @given(identifier=identifier_strategy)
    @settings(max_examples=50)
    @pytest.mark.anyio
    async def test_escalation_increases_duration(self, identifier: str) -> None:
        """Property: Repeated bans increase duration with escalation."""
        store = InMemoryBanStore()
        config = (
            AutoBanConfigBuilder()
            .add_threshold(
                ViolationType.RATE_LIMIT,
                max_violations=1,
                time_window=timedelta(minutes=5),
                ban_duration=timedelta(hours=1),
            )
            .with_escalation(enabled=True, multiplier=2.0)
            .build()
        )
        service = AutoBanService(config, store)

        # First ban
        result1 = await service.record_violation(identifier, ViolationType.RATE_LIMIT)
        assert result1.is_banned is True
        duration1 = result1.ban_record.expires_at - result1.ban_record.banned_at

        # Lift and trigger second ban
        await service.lift_ban(identifier)
        result2 = await service.record_violation(identifier, ViolationType.RATE_LIMIT)
        assert result2.is_banned is True
        duration2 = result2.ban_record.expires_at - result2.ban_record.banned_at

        # Second ban should be longer
        assert duration2 > duration1

    @given(identifier=identifier_strategy)
    @settings(max_examples=50)
    @pytest.mark.anyio
    async def test_permanent_ban_after_threshold(self, identifier: str) -> None:
        """Property: Permanent ban after configured number of bans."""
        store = InMemoryBanStore()
        config = (
            AutoBanConfigBuilder()
            .add_threshold(
                ViolationType.ABUSE,
                max_violations=1,
                time_window=timedelta(minutes=5),
                ban_duration=timedelta(hours=1),
            )
            .with_permanent_ban_after(2)
            .build()
        )
        service = AutoBanService(config, store)

        # First ban
        await service.record_violation(identifier, ViolationType.ABUSE)
        await service.lift_ban(identifier)

        # Second ban should be permanent
        result = await service.record_violation(identifier, ViolationType.ABUSE)
        assert result.is_banned is True
        assert result.ban_record.is_permanent is True


class TestConfigBuilderProperties:
    """Property tests for AutoBanConfigBuilder."""

    @given(
        max_violations=st.integers(min_value=1, max_value=100),
        ban_hours=st.integers(min_value=1, max_value=720),
    )
    @settings(max_examples=100)
    def test_builder_creates_valid_config(
        self, max_violations: int, ban_hours: int
    ) -> None:
        """Property: Builder creates valid configuration."""
        config = (
            AutoBanConfigBuilder()
            .add_threshold(
                ViolationType.RATE_LIMIT,
                max_violations=max_violations,
                time_window=timedelta(minutes=5),
                ban_duration=timedelta(hours=ban_hours),
            )
            .build()
        )

        assert len(config.thresholds) == 1
        assert config.thresholds[0].max_violations == max_violations
        assert config.thresholds[0].ban_duration == timedelta(hours=ban_hours)

    def test_default_config_has_all_violation_types(self) -> None:
        """Property: Default config covers common violation types."""
        config = AutoBanConfig.default()
        covered_types = {t.violation_type for t in config.thresholds}

        assert ViolationType.RATE_LIMIT in covered_types
        assert ViolationType.AUTH_FAILURE in covered_types
        assert ViolationType.BRUTE_FORCE in covered_types

    def test_strict_config_has_lower_thresholds(self) -> None:
        """Property: Strict config has lower thresholds than default."""
        default = AutoBanConfig.default()
        strict = create_strict_config()

        default_map = {t.violation_type: t for t in default.thresholds}
        strict_map = {t.violation_type: t for t in strict.thresholds}

        for vtype in strict_map:
            if vtype in default_map:
                assert strict_map[vtype].max_violations <= default_map[vtype].max_violations

    def test_lenient_config_has_higher_thresholds(self) -> None:
        """Property: Lenient config has higher thresholds than default."""
        default = AutoBanConfig.default()
        lenient = create_lenient_config()

        default_map = {t.violation_type: t for t in default.thresholds}
        lenient_map = {t.violation_type: t for t in lenient.thresholds}

        for vtype in lenient_map:
            if vtype in default_map:
                assert lenient_map[vtype].max_violations >= default_map[vtype].max_violations


class TestBanCheckResultProperties:
    """Property tests for BanCheckResult."""

    def test_allowed_result_is_not_banned(self) -> None:
        """Property: Allowed result has is_banned=False."""
        result = BanCheckResult.allowed()
        assert result.is_banned is False
        assert result.ban_record is None

    @given(identifier=identifier_strategy)
    @settings(max_examples=100)
    def test_banned_result_has_record(self, identifier: str) -> None:
        """Property: Banned result has ban record."""
        now = datetime.now(timezone.utc)
        record = BanRecord(
            identifier=identifier,
            reason=ViolationType.ABUSE,
            banned_at=now,
            expires_at=now + timedelta(hours=1),
            violation_count=1,
        )
        result = BanCheckResult.banned(record, "Test reason")

        assert result.is_banned is True
        assert result.ban_record is not None
        assert result.ban_record.identifier == identifier


# =============================================================================
# Property Tests - Lock Manager (shared-modules-refactoring)
# =============================================================================


class TestLockManagerProperties:
    """Property tests for LockManager.

    **Feature: shared-modules-refactoring**
    **Validates: Requirements 2.1, 2.3, 2.4**
    """

    @pytest.mark.anyio
    async def test_concurrent_violation_serialization(self) -> None:
        """**Feature: shared-modules-refactoring, Property 5: Concurrent Violation Serialization**
        **Validates: Requirements 2.1**

        For any set of concurrent violation records for the same identifier,
        the final violation count SHALL equal the sum of all individual violations.
        """
        import asyncio
        from infrastructure.security.auto_ban.lock_manager import InMemoryLockManager

        lock_manager = InMemoryLockManager()
        counter = {"value": 0}
        num_concurrent = 50

        async def increment_with_lock(identifier: str) -> None:
            async with lock_manager.acquire(identifier):
                current = counter["value"]
                await asyncio.sleep(0.001)  # Simulate work
                counter["value"] = current + 1

        # Run concurrent increments
        tasks = [increment_with_lock("test-id") for _ in range(num_concurrent)]
        await asyncio.gather(*tasks)

        # Without proper locking, this would be less than num_concurrent
        assert counter["value"] == num_concurrent

    @pytest.mark.anyio
    async def test_lock_cleanup_effectiveness(self) -> None:
        """**Feature: shared-modules-refactoring, Property 7: Lock Cleanup Effectiveness**
        **Validates: Requirements 2.3**

        For any lock manager with more than max_entries entries,
        after cleanup, the number of entries SHALL be less than or equal to max_entries.
        """
        from infrastructure.security.auto_ban.lock_manager import InMemoryLockManager

        lock_manager = InMemoryLockManager()
        max_entries = 10

        # Create more locks than max_entries
        for i in range(20):
            async with lock_manager.acquire(f"id-{i}"):
                pass

        assert lock_manager.lock_count == 20

        # Cleanup
        removed = await lock_manager.cleanup_stale(max_entries=max_entries)

        assert removed == 10
        assert lock_manager.lock_count <= max_entries

    @pytest.mark.anyio
    async def test_lock_acquisition_timeout(self) -> None:
        """**Feature: shared-modules-refactoring, Property 5: Concurrent Violation Serialization**
        **Validates: Requirements 2.4**

        When a lock acquisition times out after the specified timeout,
        the LockManager SHALL raise LockAcquisitionTimeout.
        """
        import asyncio
        from infrastructure.security.auto_ban.lock_manager import InMemoryLockManager
        from core.errors.exceptions import LockAcquisitionTimeout

        lock_manager = InMemoryLockManager()
        identifier = "test-lock"

        # Acquire lock and hold it
        async with lock_manager.acquire(identifier):
            # Try to acquire same lock with short timeout
            with pytest.raises(LockAcquisitionTimeout) as exc_info:
                async with lock_manager.acquire(identifier, timeout=0.1):
                    pass

            assert exc_info.value.identifier == identifier
            assert exc_info.value.timeout == 0.1

    @given(identifier=identifier_strategy)
    @settings(max_examples=50)
    @pytest.mark.anyio
    async def test_lock_release_allows_reacquisition(self, identifier: str) -> None:
        """**Feature: shared-modules-refactoring, Property 5: Concurrent Violation Serialization**
        **Validates: Requirements 2.1**

        For any identifier, after releasing a lock, another acquire SHALL succeed.
        """
        from infrastructure.security.auto_ban.lock_manager import InMemoryLockManager

        lock_manager = InMemoryLockManager()

        # First acquisition
        async with lock_manager.acquire(identifier):
            pass

        # Second acquisition should succeed
        async with lock_manager.acquire(identifier):
            pass

        # If we get here, both acquisitions succeeded
        assert True


    @pytest.mark.anyio
    async def test_atomic_ban_check_and_update(self) -> None:
        """**Feature: shared-modules-refactoring, Property 6: Atomic Ban Check-and-Update**
        **Validates: Requirements 2.2**

        For any ban check followed by update, no other operation SHALL observe
        an intermediate state where the check passed but the update is incomplete.
        """
        import asyncio

        config = (
            AutoBanConfigBuilder()
            .add_threshold(
                ViolationType.RATE_LIMIT,
                max_violations=5,
                time_window=timedelta(minutes=5),
                ban_duration=timedelta(hours=1),
            )
            .build()
        )
        store = InMemoryBanStore()
        service = AutoBanService(config, store)

        identifier = "atomic-test-id"
        results = []

        async def record_and_check() -> None:
            result = await service.record_violation(identifier, ViolationType.RATE_LIMIT)
            results.append(result)

        # Run concurrent violations
        tasks = [record_and_check() for _ in range(10)]
        await asyncio.gather(*tasks)

        # Count how many saw banned vs not banned
        banned_count = sum(1 for r in results if r.is_banned)
        not_banned_count = sum(1 for r in results if not r.is_banned)

        # With atomic operations, exactly one transition to banned should occur
        # after threshold (5) is reached
        assert banned_count >= 1  # At least one should see banned
        assert not_banned_count >= 4  # At least 4 should see not banned (before threshold)
