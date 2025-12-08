"""Tests for feature flags module.

Tests for FeatureFlag, FeatureFlagEvaluator, InMemoryFeatureFlagStore, and FlagAuditLogger.
"""

from datetime import UTC, datetime

import pytest

from infrastructure.feature_flags.flags import (
    EvaluationContext,
    EvaluationResult,
    FeatureFlag,
    FeatureFlagEvaluator,
    FlagAuditLogger,
    FlagEvaluationLog,
    FlagStatus,
    InMemoryFeatureFlagStore,
)


class TestFlagStatus:
    """Tests for FlagStatus enum."""

    def test_enabled_value(self) -> None:
        """ENABLED should have correct value."""
        assert FlagStatus.ENABLED.value == "enabled"

    def test_disabled_value(self) -> None:
        """DISABLED should have correct value."""
        assert FlagStatus.DISABLED.value == "disabled"

    def test_percentage_value(self) -> None:
        """PERCENTAGE should have correct value."""
        assert FlagStatus.PERCENTAGE.value == "percentage"

    def test_targeted_value(self) -> None:
        """TARGETED should have correct value."""
        assert FlagStatus.TARGETED.value == "targeted"


class TestEvaluationContext:
    """Tests for EvaluationContext dataclass."""

    def test_default_values(self) -> None:
        """EvaluationContext should have sensible defaults."""
        ctx: EvaluationContext[None] = EvaluationContext()
        assert ctx.user_id is None
        assert ctx.groups == ()
        assert ctx.attributes == {}
        assert ctx.context_data is None

    def test_with_user_id(self) -> None:
        """EvaluationContext should store user_id."""
        ctx: EvaluationContext[None] = EvaluationContext(user_id="user-123")
        assert ctx.user_id == "user-123"

    def test_with_groups(self) -> None:
        """EvaluationContext should store groups."""
        ctx: EvaluationContext[None] = EvaluationContext(groups=("beta", "premium"))
        assert "beta" in ctx.groups
        assert "premium" in ctx.groups

    def test_with_attributes(self) -> None:
        """EvaluationContext should store attributes."""
        ctx: EvaluationContext[None] = EvaluationContext(
            attributes={"country": "US", "plan": "pro"}
        )
        assert ctx.attributes["country"] == "US"

    def test_is_frozen(self) -> None:
        """EvaluationContext should be immutable."""
        ctx: EvaluationContext[None] = EvaluationContext(user_id="user")
        with pytest.raises(AttributeError):
            ctx.user_id = "other"  # type: ignore


class TestFeatureFlag:
    """Tests for FeatureFlag dataclass."""

    def test_init_required_fields(self) -> None:
        """FeatureFlag should store required fields."""
        flag: FeatureFlag[None] = FeatureFlag(key="my-flag", name="My Flag")
        assert flag.key == "my-flag"
        assert flag.name == "My Flag"

    def test_default_status_disabled(self) -> None:
        """FeatureFlag should be disabled by default."""
        flag: FeatureFlag[None] = FeatureFlag(key="test", name="Test")
        assert flag.status == FlagStatus.DISABLED

    def test_is_enabled_for_disabled_flag(self) -> None:
        """Disabled flag should return False."""
        flag: FeatureFlag[None] = FeatureFlag(
            key="test", name="Test", status=FlagStatus.DISABLED
        )
        ctx: EvaluationContext[None] = EvaluationContext(user_id="user-1")
        assert flag.is_enabled_for(ctx) is False

    def test_is_enabled_for_enabled_flag(self) -> None:
        """Enabled flag should return True."""
        flag: FeatureFlag[None] = FeatureFlag(
            key="test", name="Test", status=FlagStatus.ENABLED
        )
        ctx: EvaluationContext[None] = EvaluationContext(user_id="user-1")
        assert flag.is_enabled_for(ctx) is True

    def test_is_enabled_for_disabled_user(self) -> None:
        """Disabled user should return False even if flag enabled."""
        flag: FeatureFlag[None] = FeatureFlag(
            key="test",
            name="Test",
            status=FlagStatus.ENABLED,
            disabled_users={"blocked-user"},
        )
        ctx: EvaluationContext[None] = EvaluationContext(user_id="blocked-user")
        assert flag.is_enabled_for(ctx) is False

    def test_is_enabled_for_targeted_user(self) -> None:
        """Targeted user should return True."""
        flag: FeatureFlag[None] = FeatureFlag(
            key="test",
            name="Test",
            status=FlagStatus.TARGETED,
            enabled_users={"vip-user"},
        )
        ctx: EvaluationContext[None] = EvaluationContext(user_id="vip-user")
        assert flag.is_enabled_for(ctx) is True

    def test_is_enabled_for_targeted_group(self) -> None:
        """User in targeted group should return True."""
        flag: FeatureFlag[None] = FeatureFlag(
            key="test",
            name="Test",
            status=FlagStatus.TARGETED,
            enabled_groups={"beta-testers"},
        )
        ctx: EvaluationContext[None] = EvaluationContext(
            user_id="user-1", groups=("beta-testers",)
        )
        assert flag.is_enabled_for(ctx) is True

    def test_is_enabled_for_not_in_target_group(self) -> None:
        """User not in targeted group should return False."""
        flag: FeatureFlag[None] = FeatureFlag(
            key="test",
            name="Test",
            status=FlagStatus.TARGETED,
            enabled_groups={"beta-testers"},
        )
        ctx: EvaluationContext[None] = EvaluationContext(
            user_id="user-1", groups=("regular",)
        )
        assert flag.is_enabled_for(ctx) is False

    def test_percentage_rollout_consistent(self) -> None:
        """Percentage rollout should be consistent for same user."""
        flag: FeatureFlag[None] = FeatureFlag(
            key="test", name="Test", status=FlagStatus.PERCENTAGE, percentage=50.0
        )
        ctx: EvaluationContext[None] = EvaluationContext(user_id="user-123")
        # Same user should get same result
        result1 = flag.is_enabled_for(ctx)
        result2 = flag.is_enabled_for(ctx)
        assert result1 == result2

    def test_percentage_rollout_100_percent(self) -> None:
        """100% rollout should enable for all users."""
        flag: FeatureFlag[None] = FeatureFlag(
            key="test", name="Test", status=FlagStatus.PERCENTAGE, percentage=100.0
        )
        ctx: EvaluationContext[None] = EvaluationContext(user_id="any-user")
        assert flag.is_enabled_for(ctx) is True

    def test_percentage_rollout_0_percent(self) -> None:
        """0% rollout should disable for all users."""
        flag: FeatureFlag[None] = FeatureFlag(
            key="test", name="Test", status=FlagStatus.PERCENTAGE, percentage=0.0
        )
        ctx: EvaluationContext[None] = EvaluationContext(user_id="any-user")
        assert flag.is_enabled_for(ctx) is False


class TestEvaluationResult:
    """Tests for EvaluationResult dataclass."""

    def test_init_required_fields(self) -> None:
        """EvaluationResult should store required fields."""
        result = EvaluationResult(flag_key="test", enabled=True, reason="FLAG_ENABLED")
        assert result.flag_key == "test"
        assert result.enabled is True
        assert result.reason == "FLAG_ENABLED"

    def test_default_variant(self) -> None:
        """EvaluationResult should have None variant by default."""
        result = EvaluationResult(flag_key="test", enabled=True, reason="test")
        assert result.variant is None

    def test_is_frozen(self) -> None:
        """EvaluationResult should be immutable."""
        result = EvaluationResult(flag_key="test", enabled=True, reason="test")
        with pytest.raises(AttributeError):
            result.enabled = False  # type: ignore


class TestFeatureFlagEvaluator:
    """Tests for FeatureFlagEvaluator class."""

    def test_register_flag(self) -> None:
        """register should add flag to evaluator."""
        evaluator: FeatureFlagEvaluator[None] = FeatureFlagEvaluator()
        flag: FeatureFlag[None] = FeatureFlag(
            key="test", name="Test", status=FlagStatus.ENABLED
        )
        evaluator.register(flag)
        ctx: EvaluationContext[None] = EvaluationContext()
        assert evaluator.is_enabled("test", ctx) is True

    def test_evaluate_not_found(self) -> None:
        """evaluate should return FLAG_NOT_FOUND for unknown flag."""
        evaluator: FeatureFlagEvaluator[None] = FeatureFlagEvaluator()
        ctx: EvaluationContext[None] = EvaluationContext()
        result = evaluator.evaluate("unknown", ctx)
        assert result.enabled is False
        assert result.reason == "FLAG_NOT_FOUND"

    def test_evaluate_disabled_flag(self) -> None:
        """evaluate should return FLAG_DISABLED reason."""
        evaluator: FeatureFlagEvaluator[None] = FeatureFlagEvaluator()
        flag: FeatureFlag[None] = FeatureFlag(
            key="test", name="Test", status=FlagStatus.DISABLED
        )
        evaluator.register(flag)
        ctx: EvaluationContext[None] = EvaluationContext()
        result = evaluator.evaluate("test", ctx)
        assert result.reason == "FLAG_DISABLED"

    def test_evaluate_enabled_flag(self) -> None:
        """evaluate should return FLAG_ENABLED reason."""
        evaluator: FeatureFlagEvaluator[None] = FeatureFlagEvaluator()
        flag: FeatureFlag[None] = FeatureFlag(
            key="test", name="Test", status=FlagStatus.ENABLED
        )
        evaluator.register(flag)
        ctx: EvaluationContext[None] = EvaluationContext()
        result = evaluator.evaluate("test", ctx)
        assert result.reason == "FLAG_ENABLED"

    def test_evaluate_user_disabled(self) -> None:
        """evaluate should return USER_DISABLED reason."""
        evaluator: FeatureFlagEvaluator[None] = FeatureFlagEvaluator()
        flag: FeatureFlag[None] = FeatureFlag(
            key="test",
            name="Test",
            status=FlagStatus.ENABLED,
            disabled_users={"blocked"},
        )
        evaluator.register(flag)
        ctx: EvaluationContext[None] = EvaluationContext(user_id="blocked")
        result = evaluator.evaluate("test", ctx)
        assert result.reason == "USER_DISABLED"

    def test_is_enabled_shortcut(self) -> None:
        """is_enabled should return boolean directly."""
        evaluator: FeatureFlagEvaluator[None] = FeatureFlagEvaluator()
        flag: FeatureFlag[None] = FeatureFlag(
            key="test", name="Test", status=FlagStatus.ENABLED
        )
        evaluator.register(flag)
        ctx: EvaluationContext[None] = EvaluationContext()
        assert evaluator.is_enabled("test", ctx) is True


class TestInMemoryFeatureFlagStore:
    """Tests for InMemoryFeatureFlagStore class."""

    @pytest.mark.asyncio
    async def test_save_and_get(self) -> None:
        """save and get should work together."""
        store: InMemoryFeatureFlagStore[None] = InMemoryFeatureFlagStore()
        flag: FeatureFlag[None] = FeatureFlag(key="test", name="Test")
        await store.save(flag)
        retrieved = await store.get("test")
        assert retrieved == flag

    @pytest.mark.asyncio
    async def test_get_not_found(self) -> None:
        """get should return None for unknown key."""
        store: InMemoryFeatureFlagStore[None] = InMemoryFeatureFlagStore()
        result = await store.get("unknown")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all(self) -> None:
        """get_all should return all flags."""
        store: InMemoryFeatureFlagStore[None] = InMemoryFeatureFlagStore()
        flag1: FeatureFlag[None] = FeatureFlag(key="flag1", name="Flag 1")
        flag2: FeatureFlag[None] = FeatureFlag(key="flag2", name="Flag 2")
        await store.save(flag1)
        await store.save(flag2)
        all_flags = await store.get_all()
        assert len(all_flags) == 2

    @pytest.mark.asyncio
    async def test_delete_existing(self) -> None:
        """delete should return True for existing flag."""
        store: InMemoryFeatureFlagStore[None] = InMemoryFeatureFlagStore()
        flag: FeatureFlag[None] = FeatureFlag(key="test", name="Test")
        await store.save(flag)
        result = await store.delete("test")
        assert result is True
        assert await store.get("test") is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self) -> None:
        """delete should return False for unknown key."""
        store: InMemoryFeatureFlagStore[None] = InMemoryFeatureFlagStore()
        result = await store.delete("unknown")
        assert result is False


class TestFlagAuditLogger:
    """Tests for FlagAuditLogger class."""

    def test_log_evaluation(self) -> None:
        """log_evaluation should store log entry."""
        logger = FlagAuditLogger()
        result = EvaluationResult(flag_key="test", enabled=True, reason="FLAG_ENABLED")
        ctx: EvaluationContext[None] = EvaluationContext(user_id="user-1")
        logger.log_evaluation(result, ctx)
        logs = logger.get_logs()
        assert len(logs) == 1
        assert logs[0].flag_key == "test"
        assert logs[0].user_id == "user-1"

    def test_get_logs_filtered(self) -> None:
        """get_logs should filter by flag_key."""
        audit_logger = FlagAuditLogger()
        result1 = EvaluationResult(flag_key="flag1", enabled=True, reason="test")
        result2 = EvaluationResult(flag_key="flag2", enabled=False, reason="test")
        ctx: EvaluationContext[None] = EvaluationContext()
        audit_logger.log_evaluation(result1, ctx)
        audit_logger.log_evaluation(result2, ctx)
        logs = audit_logger.get_logs("flag1")
        assert len(logs) == 1
        assert logs[0].flag_key == "flag1"

    def test_get_logs_all(self) -> None:
        """get_logs without filter should return all."""
        audit_logger = FlagAuditLogger()
        result1 = EvaluationResult(flag_key="flag1", enabled=True, reason="test")
        result2 = EvaluationResult(flag_key="flag2", enabled=False, reason="test")
        ctx: EvaluationContext[None] = EvaluationContext()
        audit_logger.log_evaluation(result1, ctx)
        audit_logger.log_evaluation(result2, ctx)
        logs = audit_logger.get_logs()
        assert len(logs) == 2


class TestFlagEvaluationLog:
    """Tests for FlagEvaluationLog dataclass."""

    def test_init_required_fields(self) -> None:
        """FlagEvaluationLog should store required fields."""
        log = FlagEvaluationLog(
            flag_key="test",
            user_id="user-1",
            result=True,
            reason="FLAG_ENABLED",
            timestamp=datetime.now(UTC),
            context_attributes={},
        )
        assert log.flag_key == "test"
        assert log.user_id == "user-1"
        assert log.result is True

    def test_is_frozen(self) -> None:
        """FlagEvaluationLog should be immutable."""
        log = FlagEvaluationLog(
            flag_key="test",
            user_id="user-1",
            result=True,
            reason="test",
            timestamp=datetime.now(UTC),
            context_attributes={},
        )
        with pytest.raises(AttributeError):
            log.result = False  # type: ignore
