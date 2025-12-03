"""feature_flags service.

Refactored with Strategy pattern for extensible flag evaluation.

**Feature: application-layer-improvements-2025**
**Validates: Strategy pattern refactoring**
"""

import logging
from datetime import datetime, UTC
from typing import Any
from pydantic import BaseModel
from .enums import FlagStatus
from .models import EvaluationContext
from .config import FlagConfig
from .strategies import (
    StrategyChain,
    CustomRuleStrategy,
    create_default_strategy_chain,
)

logger = logging.getLogger(__name__)


class FlagEvaluation(BaseModel):
    """Result of flag evaluation.

    Attributes:
        flag_key: Flag key.
        value: Evaluated value.
        reason: Reason for the value.
        is_default: Whether default value was used.
    """

    flag_key: str
    value: Any
    reason: str
    is_default: bool = False


class FeatureFlagService:
    """Feature flag service with strategy-based evaluation.

    Provides feature flag management with:
    - Extensible evaluation strategies
    - Percentage-based rollouts
    - User targeting
    - Group targeting
    - Custom rules

    **Refactored: 2025 - Strategy pattern for extensibility**
    """

    def __init__(
        self,
        seed: int | None = None,
        strategy_chain: StrategyChain | None = None,
    ) -> None:
        """Initialize feature flag service.

        Args:
            seed: Random seed for consistent hashing (used in default chain).
            strategy_chain: Optional custom strategy chain. If not provided,
                          uses default chain with standard strategies.
        """
        self._flags: dict[str, FlagConfig] = {}
        self._seed = seed or 0
        self._strategy_chain = strategy_chain or create_default_strategy_chain(self._seed)

    def register_flag(self, config: FlagConfig) -> None:
        """Register a feature flag.

        Args:
            config: Flag configuration.
        """
        self._flags[config.key] = config

    def unregister_flag(self, key: str) -> bool:
        """Unregister a feature flag.

        Args:
            key: Flag key.

        Returns:
            True if flag was removed.
        """
        if key in self._flags:
            del self._flags[key]
            return True
        return False

    def get_flag(self, key: str) -> FlagConfig | None:
        """Get flag configuration.

        Args:
            key: Flag key.

        Returns:
            Flag config or None.
        """
        return self._flags.get(key)

    def list_flags(self) -> list[FlagConfig]:
        """List all registered flags.

        Returns:
            List of flag configurations.
        """
        return list(self._flags.values())

    def set_custom_rule(
        self,
        flag_key: str,
        rule: Any,
    ) -> None:
        """Set a custom evaluation rule for a flag.

        Args:
            flag_key: Flag key.
            rule: Custom rule function that takes EvaluationContext and returns bool.
        """
        # Find CustomRuleStrategy in chain and register rule
        for strategy in self._strategy_chain._strategies:
            if isinstance(strategy, CustomRuleStrategy):
                strategy.register_rule(flag_key, rule)
                return

        logger.warning(
            "custom_rule_strategy_not_found",
            extra={
                "flag_key": flag_key,
                "operation": "SET_CUSTOM_RULE_WARNING",
            },
        )

    def is_enabled(
        self,
        key: str,
        context: EvaluationContext | None = None,
    ) -> bool:
        """Check if a flag is enabled.

        Args:
            key: Flag key.
            context: Evaluation context.

        Returns:
            True if flag is enabled.
        """
        evaluation = self.evaluate(key, context)
        return bool(evaluation.value)

    def evaluate(
        self,
        key: str,
        context: EvaluationContext | None = None,
    ) -> FlagEvaluation:
        """Evaluate a feature flag using strategy chain.

        **Refactored: 2025 - Strategy pattern for extensibility (complexity: 3)**

        Args:
            key: Flag key to evaluate.
            context: Evaluation context (user, groups, attributes).

        Returns:
            Flag evaluation result with value, reason, and default flag.

        Example:
            >>> service = FeatureFlagService()
            >>> context = EvaluationContext(user_id="123", groups=["beta"])
            >>> result = service.evaluate("new_feature", context)
            >>> if result.value:
            ...     # Feature enabled
        """
        context = context or EvaluationContext()

        flag = self._flags.get(key)
        if not flag:
            logger.debug(
                "flag_not_found",
                extra={
                    "flag_key": key,
                    "operation": "FLAG_EVALUATION",
                },
            )
            return FlagEvaluation(
                flag_key=key, value=False, reason="Flag not found", is_default=True
            )

        # Delegate evaluation to strategy chain
        value, reason = self._strategy_chain.evaluate(flag, context)

        # Determine if default value was returned
        is_default = value == flag.default_value and (
            flag.status == FlagStatus.DISABLED or reason == "No matching rules"
        )

        return FlagEvaluation(
            flag_key=key,
            value=value,
            reason=reason,
            is_default=is_default,
        )

    def enable_flag(self, key: str) -> bool:
        """Enable a flag.

        Args:
            key: Flag key.

        Returns:
            True if flag was enabled.
        """
        flag = self._flags.get(key)
        if flag:
            flag.status = FlagStatus.ENABLED
            flag.updated_at = datetime.now(UTC)
            return True
        return False

    def disable_flag(self, key: str) -> bool:
        """Disable a flag.

        Args:
            key: Flag key.

        Returns:
            True if flag was disabled.
        """
        flag = self._flags.get(key)
        if flag:
            flag.status = FlagStatus.DISABLED
            flag.updated_at = datetime.now(UTC)
            return True
        return False

    def set_percentage(self, key: str, percentage: float) -> bool:
        """Set percentage rollout for a flag.

        Args:
            key: Flag key.
            percentage: Rollout percentage (0-100).

        Returns:
            True if percentage was set.
        """
        flag = self._flags.get(key)
        if flag:
            flag.status = FlagStatus.PERCENTAGE
            flag.percentage = max(0, min(100, percentage))
            flag.updated_at = datetime.now(UTC)
            return True
        return False

    def add_user_target(self, key: str, user_id: str) -> bool:
        """Add user to flag targeting.

        Args:
            key: Flag key.
            user_id: User ID to target.

        Returns:
            True if user was added.
        """
        flag = self._flags.get(key)
        if flag:
            if user_id not in flag.user_ids:
                flag.user_ids.append(user_id)
            flag.status = FlagStatus.TARGETED
            flag.updated_at = datetime.now(UTC)
            return True
        return False

    def remove_user_target(self, key: str, user_id: str) -> bool:
        """Remove user from flag targeting.

        Args:
            key: Flag key.
            user_id: User ID to remove.

        Returns:
            True if user was removed.
        """
        flag = self._flags.get(key)
        if flag and user_id in flag.user_ids:
            flag.user_ids.remove(user_id)
            flag.updated_at = datetime.now(UTC)
            return True
        return False


def create_flag(
    key: str,
    name: str = "",
    enabled: bool = False,
    percentage: float | None = None,
) -> FlagConfig:
    """Create a feature flag configuration.

    Args:
        key: Flag key.
        name: Flag name.
        enabled: Whether flag is enabled.
        percentage: Optional percentage rollout.

    Returns:
        Flag configuration.
    """
    status = FlagStatus.ENABLED if enabled else FlagStatus.DISABLED
    if percentage is not None:
        status = FlagStatus.PERCENTAGE

    return FlagConfig(
        key=key,
        name=name or key,
        status=status,
        percentage=percentage or 0.0,
    )
