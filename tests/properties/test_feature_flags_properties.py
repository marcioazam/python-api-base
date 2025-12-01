"""Property tests for feature_flags module.

**Feature: shared-modules-phase2**
**Validates: Requirements 7.1, 7.2, 8.1**
"""

import pytest
from hypothesis import given, settings, strategies as st

from my_app.application.feature_flags import (
    EvaluationContext,
    FeatureFlagService,
    FlagConfig,
    FlagStatus,
    create_flag,
)


class TestPercentageRolloutConsistency:
    """Property tests for percentage rollout consistency.

    **Feature: shared-modules-phase2, Property 12: Percentage Rollout Consistency**
    **Validates: Requirements 7.1**
    """

    @settings(max_examples=100)
    @given(
        user_id=st.text(min_size=1, max_size=50),
        percentage=st.floats(min_value=0.0, max_value=100.0),
    )
    def test_same_user_same_result(self, user_id: str, percentage: float) -> None:
        """Same user should get same result across evaluations."""
        service = FeatureFlagService(seed=42)
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.PERCENTAGE,
            percentage=percentage,
        )
        service.register_flag(flag)

        context = EvaluationContext(user_id=user_id)

        # Evaluate multiple times
        results = [service.is_enabled("test-flag", context) for _ in range(10)]

        # All results should be the same
        assert len(set(results)) == 1

    @settings(max_examples=100)
    @given(user_id=st.text(min_size=1, max_size=50))
    def test_100_percent_always_enabled(self, user_id: str) -> None:
        """100% rollout should always be enabled."""
        service = FeatureFlagService()
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.PERCENTAGE,
            percentage=100.0,
        )
        service.register_flag(flag)

        context = EvaluationContext(user_id=user_id)
        assert service.is_enabled("test-flag", context) is True

    @settings(max_examples=100)
    @given(user_id=st.text(min_size=1, max_size=50))
    def test_0_percent_always_disabled(self, user_id: str) -> None:
        """0% rollout should always be disabled."""
        service = FeatureFlagService()
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.PERCENTAGE,
            percentage=0.0,
        )
        service.register_flag(flag)

        context = EvaluationContext(user_id=user_id)
        assert service.is_enabled("test-flag", context) is False


class TestRolloutMonotonicity:
    """Property tests for rollout monotonicity.

    **Feature: shared-modules-phase2, Property 13: Rollout Monotonicity**
    **Validates: Requirements 7.2**
    """

    @settings(max_examples=100)
    @given(
        user_id=st.text(min_size=1, max_size=50),
        initial_percentage=st.floats(min_value=0.0, max_value=50.0),
    )
    def test_increasing_percentage_keeps_users(
        self, user_id: str, initial_percentage: float
    ) -> None:
        """Increasing percentage should not remove users from rollout."""
        service = FeatureFlagService(seed=42)
        flag = FlagConfig(
            key="test-flag",
            status=FlagStatus.PERCENTAGE,
            percentage=initial_percentage,
        )
        service.register_flag(flag)

        context = EvaluationContext(user_id=user_id)
        initial_result = service.is_enabled("test-flag", context)

        # Increase percentage
        service.set_percentage("test-flag", initial_percentage + 50.0)
        new_result = service.is_enabled("test-flag", context)

        # If user was in rollout, they should still be in
        if initial_result:
            assert new_result is True


class TestFlagOperations:
    """Test flag enable/disable operations."""

    def test_enable_flag(self) -> None:
        """Enable flag should work correctly."""
        service = FeatureFlagService()
        flag = create_flag("test-flag", enabled=False)
        service.register_flag(flag)

        assert service.is_enabled("test-flag") is False

        service.enable_flag("test-flag")
        assert service.is_enabled("test-flag") is True

    def test_disable_flag(self) -> None:
        """Disable flag should work correctly."""
        service = FeatureFlagService()
        flag = create_flag("test-flag", enabled=True)
        service.register_flag(flag)

        assert service.is_enabled("test-flag") is True

        service.disable_flag("test-flag")
        assert service.is_enabled("test-flag") is False

    def test_user_targeting(self) -> None:
        """User targeting should work correctly."""
        service = FeatureFlagService()
        flag = FlagConfig(key="test-flag", status=FlagStatus.DISABLED)
        service.register_flag(flag)

        service.add_user_target("test-flag", "user-123")

        context = EvaluationContext(user_id="user-123")
        assert service.is_enabled("test-flag", context) is True

        context_other = EvaluationContext(user_id="user-456")
        assert service.is_enabled("test-flag", context_other) is False
