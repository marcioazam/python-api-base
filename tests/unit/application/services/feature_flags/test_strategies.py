"""Unit tests for feature flag evaluation strategies.

Tests DisabledStrategy, EnabledStrategy, and other evaluation strategies.
"""

import pytest

from application.services.feature_flags.config import FlagConfig
from application.services.feature_flags.core import FlagStatus
from application.services.feature_flags.core.base import FlagEvaluationResult
from application.services.feature_flags.models import EvaluationContext
from application.services.feature_flags.strategies.status import (
    DisabledStrategy,
    EnabledStrategy,
)


class TestFlagEvaluationResult:
    """Tests for FlagEvaluationResult class."""

    def test_no_match(self) -> None:
        """Test no_match factory method."""
        result = FlagEvaluationResult.no_match()

        assert result.matched is False
        assert result.value is None
        assert result.reason == "No match"

    def test_match(self) -> None:
        """Test match factory method."""
        result = FlagEvaluationResult.match(value=True, reason="Test reason")

        assert result.matched is True
        assert result.value is True
        assert result.reason == "Test reason"

    def test_match_with_complex_value(self) -> None:
        """Test match with complex value."""
        value = {"feature": "enabled", "variant": "A"}
        result = FlagEvaluationResult.match(value=value, reason="Complex value")

        assert result.matched is True
        assert result.value == value


class TestDisabledStrategy:
    """Tests for DisabledStrategy."""

    @pytest.fixture
    def strategy(self) -> DisabledStrategy:
        """Create strategy instance."""
        return DisabledStrategy()

    @pytest.fixture
    def context(self) -> EvaluationContext:
        """Create evaluation context."""
        return EvaluationContext(user_id="user-1")

    def test_priority(self, strategy: DisabledStrategy) -> None:
        """Test strategy has highest priority."""
        assert strategy.priority == 0

    def test_evaluate_disabled_flag(
        self, strategy: DisabledStrategy, context: EvaluationContext
    ) -> None:
        """Test evaluation returns default value for disabled flag."""
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.DISABLED,
            default_value=False,
            enabled_value=True,
        )

        result = strategy.evaluate(flag, context)

        assert result.matched is True
        assert result.value is False
        assert "disabled" in result.reason.lower()


    def test_evaluate_enabled_flag_no_match(
        self, strategy: DisabledStrategy, context: EvaluationContext
    ) -> None:
        """Test evaluation returns no match for enabled flag."""
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.ENABLED,
            default_value=False,
            enabled_value=True,
        )

        result = strategy.evaluate(flag, context)

        assert result.matched is False

    def test_evaluate_percentage_flag_no_match(
        self, strategy: DisabledStrategy, context: EvaluationContext
    ) -> None:
        """Test evaluation returns no match for percentage flag."""
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.PERCENTAGE,
            default_value=False,
            enabled_value=True,
            percentage=50.0,
        )

        result = strategy.evaluate(flag, context)

        assert result.matched is False


class TestEnabledStrategy:
    """Tests for EnabledStrategy."""

    @pytest.fixture
    def strategy(self) -> EnabledStrategy:
        """Create strategy instance."""
        return EnabledStrategy()

    @pytest.fixture
    def context(self) -> EvaluationContext:
        """Create evaluation context."""
        return EvaluationContext(user_id="user-1")

    def test_priority(self, strategy: EnabledStrategy) -> None:
        """Test strategy has second highest priority."""
        assert strategy.priority == 1

    def test_evaluate_enabled_flag(
        self, strategy: EnabledStrategy, context: EvaluationContext
    ) -> None:
        """Test evaluation returns enabled value for enabled flag."""
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.ENABLED,
            default_value=False,
            enabled_value=True,
        )

        result = strategy.evaluate(flag, context)

        assert result.matched is True
        assert result.value is True
        assert "enabled" in result.reason.lower()

    def test_evaluate_disabled_flag_no_match(
        self, strategy: EnabledStrategy, context: EvaluationContext
    ) -> None:
        """Test evaluation returns no match for disabled flag."""
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.DISABLED,
            default_value=False,
            enabled_value=True,
        )

        result = strategy.evaluate(flag, context)

        assert result.matched is False

    def test_evaluate_percentage_flag_no_match(
        self, strategy: EnabledStrategy, context: EvaluationContext
    ) -> None:
        """Test evaluation returns no match for percentage flag."""
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.PERCENTAGE,
            default_value=False,
            enabled_value=True,
            percentage=50.0,
        )

        result = strategy.evaluate(flag, context)

        assert result.matched is False

    def test_evaluate_with_custom_enabled_value(
        self, strategy: EnabledStrategy, context: EvaluationContext
    ) -> None:
        """Test evaluation returns custom enabled value."""
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.ENABLED,
            default_value="default",
            enabled_value={"variant": "A", "config": {"limit": 100}},
        )

        result = strategy.evaluate(flag, context)

        assert result.matched is True
        assert result.value == {"variant": "A", "config": {"limit": 100}}


class TestFlagConfig:
    """Tests for FlagConfig dataclass."""

    def test_default_values(self) -> None:
        """Test FlagConfig default values."""
        flag = FlagConfig(key="test-flag")

        assert flag.key == "test-flag"
        assert flag.name == ""
        assert flag.description == ""
        assert flag.status == FlagStatus.DISABLED
        assert flag.default_value is False
        assert flag.enabled_value is True
        assert flag.percentage == 0.0
        assert flag.user_ids == []
        assert flag.groups == []

    def test_custom_values(self) -> None:
        """Test FlagConfig with custom values."""
        flag = FlagConfig(
            key="feature-x",
            name="Feature X",
            description="New feature X",
            status=FlagStatus.PERCENTAGE,
            default_value=False,
            enabled_value=True,
            percentage=25.0,
            user_ids=["user-1", "user-2"],
            groups=["beta-testers"],
        )

        assert flag.key == "feature-x"
        assert flag.name == "Feature X"
        assert flag.status == FlagStatus.PERCENTAGE
        assert flag.percentage == 25.0
        assert len(flag.user_ids) == 2
        assert "beta-testers" in flag.groups


class TestEvaluationContext:
    """Tests for EvaluationContext dataclass."""

    def test_default_values(self) -> None:
        """Test EvaluationContext default values."""
        context = EvaluationContext()

        assert context.user_id is None
        assert context.groups == []
        assert context.attributes == {}

    def test_with_user_id(self) -> None:
        """Test EvaluationContext with user ID."""
        context = EvaluationContext(user_id="user-123")

        assert context.user_id == "user-123"

    def test_with_groups(self) -> None:
        """Test EvaluationContext with groups."""
        context = EvaluationContext(
            user_id="user-123",
            groups=["admin", "beta-testers"],
        )

        assert len(context.groups) == 2
        assert "admin" in context.groups

    def test_with_attributes(self) -> None:
        """Test EvaluationContext with attributes."""
        context = EvaluationContext(
            user_id="user-123",
            attributes={"country": "BR", "plan": "premium"},
        )

        assert context.attributes["country"] == "BR"
        assert context.attributes["plan"] == "premium"


class TestPercentageRolloutStrategy:
    """Tests for PercentageRolloutStrategy."""

    @pytest.fixture
    def strategy(self) -> "PercentageRolloutStrategy":
        """Create strategy instance."""
        from application.services.feature_flags.strategies.rollout import (
            PercentageRolloutStrategy,
        )
        return PercentageRolloutStrategy(seed=42)

    @pytest.fixture
    def context(self) -> EvaluationContext:
        """Create evaluation context."""
        return EvaluationContext(user_id="user-123")

    def test_priority(self, strategy: "PercentageRolloutStrategy") -> None:
        """Test strategy priority."""
        assert strategy.priority == 20

    def test_evaluate_100_percent_rollout(
        self, strategy: "PercentageRolloutStrategy", context: EvaluationContext
    ) -> None:
        """Test 100% rollout always matches."""
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.PERCENTAGE,
            percentage=100.0,
            enabled_value=True,
        )

        result = strategy.evaluate(flag, context)

        assert result.matched is True
        assert result.value is True

    def test_evaluate_0_percent_rollout(
        self, strategy: "PercentageRolloutStrategy", context: EvaluationContext
    ) -> None:
        """Test 0% rollout never matches."""
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.PERCENTAGE,
            percentage=0.0,
            enabled_value=True,
        )

        result = strategy.evaluate(flag, context)

        assert result.matched is False

    def test_evaluate_non_percentage_flag(
        self, strategy: "PercentageRolloutStrategy", context: EvaluationContext
    ) -> None:
        """Test non-percentage flag returns no match."""
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.ENABLED,
            percentage=50.0,
            enabled_value=True,
        )

        result = strategy.evaluate(flag, context)

        assert result.matched is False

    def test_consistent_hashing(
        self, strategy: "PercentageRolloutStrategy"
    ) -> None:
        """Test same user always gets same result."""
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.PERCENTAGE,
            percentage=50.0,
            enabled_value=True,
        )
        context = EvaluationContext(user_id="consistent-user")

        results = [strategy.evaluate(flag, context) for _ in range(10)]

        # All results should be the same
        assert all(r.matched == results[0].matched for r in results)


class TestUserTargetingStrategy:
    """Tests for UserTargetingStrategy."""

    @pytest.fixture
    def strategy(self) -> "UserTargetingStrategy":
        """Create strategy instance."""
        from application.services.feature_flags.strategies.targeting import (
            UserTargetingStrategy,
        )
        return UserTargetingStrategy()

    def test_priority(self, strategy: "UserTargetingStrategy") -> None:
        """Test strategy priority."""
        assert strategy.priority == 10

    def test_evaluate_user_in_list(self, strategy: "UserTargetingStrategy") -> None:
        """Test user in targeting list matches."""
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.PERCENTAGE,
            user_ids=["user-1", "user-2", "user-3"],
            enabled_value=True,
        )
        context = EvaluationContext(user_id="user-2")

        result = strategy.evaluate(flag, context)

        assert result.matched is True
        assert result.value is True

    def test_evaluate_user_not_in_list(self, strategy: "UserTargetingStrategy") -> None:
        """Test user not in targeting list doesn't match."""
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.PERCENTAGE,
            user_ids=["user-1", "user-2"],
            enabled_value=True,
        )
        context = EvaluationContext(user_id="user-999")

        result = strategy.evaluate(flag, context)

        assert result.matched is False


class TestGroupTargetingStrategy:
    """Tests for GroupTargetingStrategy."""

    @pytest.fixture
    def strategy(self) -> "GroupTargetingStrategy":
        """Create strategy instance."""
        from application.services.feature_flags.strategies.targeting import (
            GroupTargetingStrategy,
        )
        return GroupTargetingStrategy()

    def test_priority(self, strategy: "GroupTargetingStrategy") -> None:
        """Test strategy priority."""
        assert strategy.priority == 11

    def test_evaluate_group_match(self, strategy: "GroupTargetingStrategy") -> None:
        """Test group targeting matches."""
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.PERCENTAGE,
            groups=["beta-testers", "admins"],
            enabled_value=True,
        )
        context = EvaluationContext(user_id="user-1", groups=["beta-testers"])

        result = strategy.evaluate(flag, context)

        assert result.matched is True

    def test_evaluate_no_group_match(self, strategy: "GroupTargetingStrategy") -> None:
        """Test no group match returns no match."""
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.PERCENTAGE,
            groups=["admins"],
            enabled_value=True,
        )
        context = EvaluationContext(user_id="user-1", groups=["users"])

        result = strategy.evaluate(flag, context)

        assert result.matched is False


class TestStrategyChain:
    """Tests for StrategyChain and create_default_strategy_chain."""

    def test_create_default_chain(self) -> None:
        """Test creating default strategy chain."""
        from application.services.feature_flags.strategies.chain import (
            create_default_strategy_chain,
        )
        
        chain = create_default_strategy_chain()
        
        assert len(chain.get_strategies()) == 7

    def test_evaluate_disabled_flag(self) -> None:
        """Test disabled flag returns default value."""
        from application.services.feature_flags.strategies.chain import (
            create_default_strategy_chain,
        )
        
        chain = create_default_strategy_chain()
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.DISABLED,
            default_value=False,
            enabled_value=True,
        )
        context = EvaluationContext(user_id="user-1")

        value, reason = chain.evaluate(flag, context)

        assert value is False
        assert "disabled" in reason.lower()

    def test_evaluate_enabled_flag(self) -> None:
        """Test enabled flag returns enabled value."""
        from application.services.feature_flags.strategies.chain import (
            create_default_strategy_chain,
        )
        
        chain = create_default_strategy_chain()
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.ENABLED,
            default_value=False,
            enabled_value=True,
        )
        context = EvaluationContext(user_id="user-1")

        value, reason = chain.evaluate(flag, context)

        assert value is True
        assert "enabled" in reason.lower()

    def test_add_strategy(self) -> None:
        """Test adding custom strategy."""
        from application.services.feature_flags.strategies.chain import StrategyChain
        from application.services.feature_flags.strategies.fallback import (
            DefaultValueStrategy,
        )
        
        chain = StrategyChain()
        initial_count = len(chain._strategies)
        chain.add_strategy(DefaultValueStrategy())
        
        assert len(chain._strategies) == initial_count + 1

    def test_remove_strategy(self) -> None:
        """Test removing strategy by type."""
        from application.services.feature_flags.strategies.chain import (
            create_default_strategy_chain,
        )
        from application.services.feature_flags.strategies.status import (
            DisabledStrategy,
        )
        
        chain = create_default_strategy_chain()
        initial_count = len(chain.get_strategies())
        
        removed = chain.remove_strategy(DisabledStrategy)
        
        assert removed is True
        assert len(chain.get_strategies()) == initial_count - 1


class TestCustomRuleStrategy:
    """Tests for CustomRuleStrategy."""

    @pytest.fixture
    def strategy(self) -> "CustomRuleStrategy":
        """Create strategy instance."""
        from application.services.feature_flags.strategies.custom_rule import (
            CustomRuleStrategy,
        )
        return CustomRuleStrategy()

    @pytest.fixture
    def flag(self) -> FlagConfig:
        """Create test flag."""
        return FlagConfig(
            key="custom-flag",
            status=FlagStatus.PERCENTAGE,
            enabled_value=True,
        )

    @pytest.fixture
    def context(self) -> EvaluationContext:
        """Create evaluation context."""
        return EvaluationContext(user_id="user-123", attributes={"plan": "premium"})

    def test_priority(self, strategy: "CustomRuleStrategy") -> None:
        """Test strategy priority."""
        assert strategy.priority == 5

    def test_evaluate_no_rule_registered(
        self, strategy: "CustomRuleStrategy", flag: FlagConfig, context: EvaluationContext
    ) -> None:
        """Test no match when no rule registered."""
        result = strategy.evaluate(flag, context)
        assert result.matched is False

    def test_evaluate_rule_returns_true(
        self, strategy: "CustomRuleStrategy", flag: FlagConfig, context: EvaluationContext
    ) -> None:
        """Test match when rule returns True."""
        strategy.register_rule("custom-flag", lambda ctx: ctx.attributes.get("plan") == "premium")

        result = strategy.evaluate(flag, context)

        assert result.matched is True
        assert result.value is True
        assert "Custom rule" in result.reason

    def test_evaluate_rule_returns_false(
        self, strategy: "CustomRuleStrategy", flag: FlagConfig, context: EvaluationContext
    ) -> None:
        """Test no match when rule returns False."""
        strategy.register_rule("custom-flag", lambda ctx: ctx.attributes.get("plan") == "free")

        result = strategy.evaluate(flag, context)

        assert result.matched is False

    def test_evaluate_rule_raises_exception(
        self, strategy: "CustomRuleStrategy", flag: FlagConfig, context: EvaluationContext
    ) -> None:
        """Test no match when rule raises exception."""
        def failing_rule(ctx: EvaluationContext) -> bool:
            raise ValueError("Rule error")

        strategy.register_rule("custom-flag", failing_rule)

        result = strategy.evaluate(flag, context)

        assert result.matched is False

    def test_unregister_rule(
        self, strategy: "CustomRuleStrategy", flag: FlagConfig, context: EvaluationContext
    ) -> None:
        """Test unregistering a rule."""
        strategy.register_rule("custom-flag", lambda ctx: True)
        strategy.unregister_rule("custom-flag")

        result = strategy.evaluate(flag, context)

        assert result.matched is False

    def test_unregister_nonexistent_rule(self, strategy: "CustomRuleStrategy") -> None:
        """Test unregistering nonexistent rule doesn't raise."""
        strategy.unregister_rule("nonexistent-flag")  # Should not raise
