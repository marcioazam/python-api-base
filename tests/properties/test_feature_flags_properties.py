"""Property-based tests for feature flags.

**Feature: api-architecture-analysis, Task 15.7: Feature Flags**
**Validates: Requirements 10.3**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from my_api.shared.feature_flags import (
    EvaluationContext,
    FeatureFlagService,
    FlagConfig,
    FlagEvaluation,
    FlagStatus,
    create_flag,
)


# =============================================================================
# Strategies
# =============================================================================

@st.composite
def flag_key_strategy(draw: st.DrawFn) -> str:
    """Generate valid flag keys."""
    return draw(st.text(
        min_size=3,
        max_size=50,
        alphabet="abcdefghijklmnopqrstuvwxyz_-",
    ))


@st.composite
def user_id_strategy(draw: st.DrawFn) -> str:
    """Generate valid user IDs."""
    return draw(st.text(
        min_size=5,
        max_size=50,
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
    ))


# =============================================================================
# Property Tests - Flag Configuration
# =============================================================================

class TestFlagConfigProperties:
    """Property tests for flag configuration."""

    @given(key=flag_key_strategy())
    @settings(max_examples=100)
    def test_config_preserves_key(self, key: str) -> None:
        """**Property 1: Config preserves key**

        *For any* flag key, it should be preserved.

        **Validates: Requirements 10.3**
        """
        config = FlagConfig(key=key)
        assert config.key == key

    @given(status=st.sampled_from(list(FlagStatus)))
    @settings(max_examples=10)
    def test_all_statuses_valid(self, status: FlagStatus) -> None:
        """**Property 2: All statuses are valid**

        *For any* status, it should be usable in config.

        **Validates: Requirements 10.3**
        """
        config = FlagConfig(key="test", status=status)
        assert config.status == status

    def test_config_defaults(self) -> None:
        """**Property 3: Config has sensible defaults**

        Default configuration should have reasonable values.

        **Validates: Requirements 10.3**
        """
        config = FlagConfig(key="test")

        assert config.status == FlagStatus.DISABLED
        assert config.default_value is False
        assert config.enabled_value is True
        assert config.percentage == 0.0


# =============================================================================
# Property Tests - Feature Flag Service
# =============================================================================

class TestFeatureFlagServiceProperties:
    """Property tests for feature flag service."""

    @given(key=flag_key_strategy())
    @settings(max_examples=100)
    def test_register_and_get_flag(self, key: str) -> None:
        """**Property 4: Register and get flag works**

        *For any* flag, registering and getting should return it.

        **Validates: Requirements 10.3**
        """
        service = FeatureFlagService()
        config = FlagConfig(key=key)

        service.register_flag(config)
        retrieved = service.get_flag(key)

        assert retrieved is not None
        assert retrieved.key == key

    @given(key=flag_key_strategy())
    @settings(max_examples=100)
    def test_unregister_flag(self, key: str) -> None:
        """**Property 5: Unregister removes flag**

        *For any* registered flag, unregistering should remove it.

        **Validates: Requirements 10.3**
        """
        service = FeatureFlagService()
        config = FlagConfig(key=key)

        service.register_flag(config)
        removed = service.unregister_flag(key)

        assert removed is True
        assert service.get_flag(key) is None

    @given(keys=st.lists(flag_key_strategy(), min_size=1, max_size=10, unique=True))
    @settings(max_examples=50)
    def test_list_flags_returns_all(self, keys: list[str]) -> None:
        """**Property 6: List flags returns all registered**

        *For any* set of registered flags, list should return all.

        **Validates: Requirements 10.3**
        """
        service = FeatureFlagService()

        for key in keys:
            service.register_flag(FlagConfig(key=key))

        flags = service.list_flags()
        flag_keys = [f.key for f in flags]

        assert set(flag_keys) == set(keys)


# =============================================================================
# Property Tests - Flag Evaluation
# =============================================================================

class TestFlagEvaluationProperties:
    """Property tests for flag evaluation."""

    @given(key=flag_key_strategy())
    @settings(max_examples=100)
    def test_disabled_flag_returns_default(self, key: str) -> None:
        """**Property 7: Disabled flag returns default value**

        *For any* disabled flag, evaluation should return default.

        **Validates: Requirements 10.3**
        """
        service = FeatureFlagService()
        config = FlagConfig(key=key, status=FlagStatus.DISABLED, default_value="default")

        service.register_flag(config)
        result = service.evaluate(key)

        assert result.value == "default"
        assert result.is_default is True

    @given(key=flag_key_strategy())
    @settings(max_examples=100)
    def test_enabled_flag_returns_enabled_value(self, key: str) -> None:
        """**Property 8: Enabled flag returns enabled value**

        *For any* enabled flag, evaluation should return enabled value.

        **Validates: Requirements 10.3**
        """
        service = FeatureFlagService()
        config = FlagConfig(key=key, status=FlagStatus.ENABLED, enabled_value="enabled")

        service.register_flag(config)
        result = service.evaluate(key)

        assert result.value == "enabled"
        assert result.is_default is False

    @given(key=flag_key_strategy())
    @settings(max_examples=100)
    def test_unknown_flag_returns_false(self, key: str) -> None:
        """**Property 9: Unknown flag returns false**

        *For any* unregistered flag key, evaluation should return false.

        **Validates: Requirements 10.3**
        """
        service = FeatureFlagService()
        result = service.evaluate(key)

        assert result.value is False
        assert result.is_default is True
        assert "not found" in result.reason.lower()

    @given(key=flag_key_strategy())
    @settings(max_examples=100)
    def test_is_enabled_matches_evaluate(self, key: str) -> None:
        """**Property 10: is_enabled matches evaluate**

        *For any* flag, is_enabled should match evaluate result.

        **Validates: Requirements 10.3**
        """
        service = FeatureFlagService()
        config = FlagConfig(key=key, status=FlagStatus.ENABLED)

        service.register_flag(config)

        is_enabled = service.is_enabled(key)
        evaluation = service.evaluate(key)

        assert is_enabled == bool(evaluation.value)


# =============================================================================
# Property Tests - User Targeting
# =============================================================================

class TestUserTargetingProperties:
    """Property tests for user targeting."""

    @given(
        key=flag_key_strategy(),
        user_id=user_id_strategy(),
    )
    @settings(max_examples=100)
    def test_targeted_user_gets_enabled(self, key: str, user_id: str) -> None:
        """**Property 11: Targeted user gets enabled value**

        *For any* user in target list, flag should be enabled.

        **Validates: Requirements 10.3**
        """
        service = FeatureFlagService()
        config = FlagConfig(
            key=key,
            status=FlagStatus.TARGETED,
            user_ids=[user_id],
        )

        service.register_flag(config)
        context = EvaluationContext(user_id=user_id)
        result = service.evaluate(key, context)

        assert result.value is True
        assert "targeted" in result.reason.lower()

    @given(
        key=flag_key_strategy(),
        user_id=user_id_strategy(),
        other_user=user_id_strategy(),
    )
    @settings(max_examples=100)
    def test_non_targeted_user_gets_default(
        self,
        key: str,
        user_id: str,
        other_user: str,
    ) -> None:
        """**Property 12: Non-targeted user gets default**

        *For any* user not in target list, flag should return default.

        **Validates: Requirements 10.3**
        """
        if user_id == other_user:
            return

        service = FeatureFlagService()
        config = FlagConfig(
            key=key,
            status=FlagStatus.TARGETED,
            user_ids=[user_id],
        )

        service.register_flag(config)
        context = EvaluationContext(user_id=other_user)
        result = service.evaluate(key, context)

        assert result.is_default is True

    @given(
        key=flag_key_strategy(),
        user_id=user_id_strategy(),
    )
    @settings(max_examples=100)
    def test_add_user_target(self, key: str, user_id: str) -> None:
        """**Property 13: Add user target works**

        *For any* user, adding to target should enable for them.

        **Validates: Requirements 10.3**
        """
        service = FeatureFlagService()
        config = FlagConfig(key=key)

        service.register_flag(config)
        service.add_user_target(key, user_id)

        context = EvaluationContext(user_id=user_id)
        assert service.is_enabled(key, context) is True


# =============================================================================
# Property Tests - Percentage Rollout
# =============================================================================

class TestPercentageRolloutProperties:
    """Property tests for percentage rollout."""

    @given(key=flag_key_strategy())
    @settings(max_examples=50)
    def test_zero_percent_always_disabled(self, key: str) -> None:
        """**Property 14: 0% rollout is always disabled**

        *For any* flag with 0% rollout, it should always be disabled.

        **Validates: Requirements 10.3**
        """
        service = FeatureFlagService()
        config = FlagConfig(key=key, status=FlagStatus.PERCENTAGE, percentage=0.0)

        service.register_flag(config)

        # Test with multiple users
        for i in range(10):
            context = EvaluationContext(user_id=f"user_{i}")
            assert service.is_enabled(key, context) is False

    @given(key=flag_key_strategy())
    @settings(max_examples=50)
    def test_hundred_percent_always_enabled(self, key: str) -> None:
        """**Property 15: 100% rollout is always enabled**

        *For any* flag with 100% rollout, it should always be enabled.

        **Validates: Requirements 10.3**
        """
        service = FeatureFlagService()
        config = FlagConfig(key=key, status=FlagStatus.PERCENTAGE, percentage=100.0)

        service.register_flag(config)

        # Test with multiple users
        for i in range(10):
            context = EvaluationContext(user_id=f"user_{i}")
            assert service.is_enabled(key, context) is True

    @given(
        key=flag_key_strategy(),
        user_id=user_id_strategy(),
    )
    @settings(max_examples=100)
    def test_consistent_percentage_for_user(self, key: str, user_id: str) -> None:
        """**Property 16: Percentage is consistent for same user**

        *For any* user, percentage evaluation should be consistent.

        **Validates: Requirements 10.3**
        """
        service = FeatureFlagService(seed=42)
        config = FlagConfig(key=key, status=FlagStatus.PERCENTAGE, percentage=50.0)

        service.register_flag(config)
        context = EvaluationContext(user_id=user_id)

        # Same user should get same result
        result1 = service.is_enabled(key, context)
        result2 = service.is_enabled(key, context)

        assert result1 == result2


# =============================================================================
# Property Tests - Flag Operations
# =============================================================================

class TestFlagOperationsProperties:
    """Property tests for flag operations."""

    @given(key=flag_key_strategy())
    @settings(max_examples=100)
    def test_enable_flag(self, key: str) -> None:
        """**Property 17: Enable flag works**

        *For any* flag, enabling should make it enabled.

        **Validates: Requirements 10.3**
        """
        service = FeatureFlagService()
        config = FlagConfig(key=key, status=FlagStatus.DISABLED)

        service.register_flag(config)
        service.enable_flag(key)

        assert service.is_enabled(key) is True

    @given(key=flag_key_strategy())
    @settings(max_examples=100)
    def test_disable_flag(self, key: str) -> None:
        """**Property 18: Disable flag works**

        *For any* flag, disabling should make it disabled.

        **Validates: Requirements 10.3**
        """
        service = FeatureFlagService()
        config = FlagConfig(key=key, status=FlagStatus.ENABLED)

        service.register_flag(config)
        service.disable_flag(key)

        assert service.is_enabled(key) is False

    @given(
        key=flag_key_strategy(),
        percentage=st.floats(min_value=0.0, max_value=100.0),
    )
    @settings(max_examples=100)
    def test_set_percentage(self, key: str, percentage: float) -> None:
        """**Property 19: Set percentage works**

        *For any* percentage, setting should update flag.

        **Validates: Requirements 10.3**
        """
        service = FeatureFlagService()
        config = FlagConfig(key=key)

        service.register_flag(config)
        service.set_percentage(key, percentage)

        flag = service.get_flag(key)
        assert flag is not None
        assert flag.status == FlagStatus.PERCENTAGE
        assert flag.percentage == max(0, min(100, percentage))


# =============================================================================
# Property Tests - Factory Function
# =============================================================================

class TestFactoryFunctionProperties:
    """Property tests for factory function."""

    @given(key=flag_key_strategy())
    @settings(max_examples=100)
    def test_create_flag_disabled(self, key: str) -> None:
        """**Property 20: Create flag disabled by default**

        *For any* key, create_flag should create disabled flag.

        **Validates: Requirements 10.3**
        """
        config = create_flag(key)

        assert config.key == key
        assert config.status == FlagStatus.DISABLED

    @given(key=flag_key_strategy())
    @settings(max_examples=100)
    def test_create_flag_enabled(self, key: str) -> None:
        """**Property 21: Create flag enabled works**

        *For any* key with enabled=True, flag should be enabled.

        **Validates: Requirements 10.3**
        """
        config = create_flag(key, enabled=True)

        assert config.status == FlagStatus.ENABLED

    @given(
        key=flag_key_strategy(),
        percentage=st.floats(min_value=0.0, max_value=100.0),
    )
    @settings(max_examples=100)
    def test_create_flag_with_percentage(self, key: str, percentage: float) -> None:
        """**Property 22: Create flag with percentage works**

        *For any* percentage, flag should have percentage status.

        **Validates: Requirements 10.3**
        """
        config = create_flag(key, percentage=percentage)

        assert config.status == FlagStatus.PERCENTAGE
        assert config.percentage == percentage
