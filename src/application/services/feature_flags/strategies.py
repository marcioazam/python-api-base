"""Feature flag evaluation strategies.

Implements Strategy pattern for flag evaluation logic, making the system
extensible and testable.

**Feature: application-layer-improvements-2025**
**Validates: Strategy pattern for FeatureFlagService**
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Any, Protocol
from collections.abc import Callable

from .models import EvaluationContext
from .config import FlagConfig
from .enums import FlagStatus

logger = logging.getLogger(__name__)


# =============================================================================
# Strategy Protocol
# =============================================================================


class FlagEvaluationResult:
    """Result of flag evaluation from a strategy.

    Attributes:
        matched: Whether the strategy matched (should be applied).
        value: The value to return if matched.
        reason: Human-readable reason for the result.
    """

    def __init__(self, matched: bool, value: Any, reason: str):
        self.matched = matched
        self.value = value
        self.reason = reason

    @classmethod
    def no_match(cls) -> "FlagEvaluationResult":
        """Create a no-match result."""
        return cls(matched=False, value=None, reason="No match")

    @classmethod
    def match(cls, value: Any, reason: str) -> "FlagEvaluationResult":
        """Create a match result."""
        return cls(matched=True, value=value, reason=reason)


class EvaluationStrategy(ABC):
    """Abstract base class for flag evaluation strategies.

    Each strategy implements a specific evaluation logic (custom rules,
    targeting, percentage rollout, etc).

    Strategies are evaluated in order of priority, with first match winning.
    """

    @property
    @abstractmethod
    def priority(self) -> int:
        """Strategy priority (lower = higher priority).

        Priority order determines evaluation sequence:
        - 0-9: Critical (status checks, custom rules)
        - 10-19: Targeting (user/group)
        - 20-29: Rollout (percentage)
        - 100+: Fallback (default values)
        """
        ...

    @abstractmethod
    def evaluate(
        self,
        flag: FlagConfig,
        context: EvaluationContext,
    ) -> FlagEvaluationResult:
        """Evaluate flag for the given context.

        Args:
            flag: Flag configuration.
            context: Evaluation context (user, groups, attributes).

        Returns:
            Evaluation result (matched, value, reason).
        """
        ...


# =============================================================================
# Status Strategies
# =============================================================================


class DisabledStrategy(EvaluationStrategy):
    """Strategy for disabled flags.

    Always returns default value when flag status is DISABLED.
    Highest priority to short-circuit evaluation.
    """

    @property
    def priority(self) -> int:
        return 0  # Highest priority

    def evaluate(
        self,
        flag: FlagConfig,
        context: EvaluationContext,
    ) -> FlagEvaluationResult:
        """Return default value if flag is disabled."""
        if flag.status == FlagStatus.DISABLED:
            return FlagEvaluationResult.match(
                value=flag.default_value,
                reason="Flag disabled",
            )
        return FlagEvaluationResult.no_match()


class EnabledStrategy(EvaluationStrategy):
    """Strategy for enabled flags.

    Always returns enabled value when flag status is ENABLED.
    High priority to short-circuit complex evaluation.
    """

    @property
    def priority(self) -> int:
        return 1  # Second highest priority

    def evaluate(
        self,
        flag: FlagConfig,
        context: EvaluationContext,
    ) -> FlagEvaluationResult:
        """Return enabled value if flag is enabled."""
        if flag.status == FlagStatus.ENABLED:
            return FlagEvaluationResult.match(
                value=flag.enabled_value,
                reason="Flag enabled",
            )
        return FlagEvaluationResult.no_match()


# =============================================================================
# Custom Rule Strategy
# =============================================================================


class CustomRuleStrategy(EvaluationStrategy):
    """Strategy for custom evaluation rules.

    Allows registering custom functions for specific flags.
    High priority after status checks.
    """

    def __init__(self) -> None:
        """Initialize custom rule strategy."""
        self._rules: dict[str, Callable[[EvaluationContext], bool]] = {}

    @property
    def priority(self) -> int:
        return 5  # After status, before targeting

    def register_rule(
        self,
        flag_key: str,
        rule: Callable[[EvaluationContext], bool],
    ) -> None:
        """Register a custom rule for a flag.

        Args:
            flag_key: Flag key to apply rule to.
            rule: Function that returns True if flag should be enabled.
        """
        self._rules[flag_key] = rule

    def unregister_rule(self, flag_key: str) -> None:
        """Unregister custom rule for a flag.

        Args:
            flag_key: Flag key to remove rule from.
        """
        self._rules.pop(flag_key, None)

    def evaluate(
        self,
        flag: FlagConfig,
        context: EvaluationContext,
    ) -> FlagEvaluationResult:
        """Evaluate custom rule if registered."""
        if flag.key not in self._rules:
            return FlagEvaluationResult.no_match()

        try:
            if self._rules[flag.key](context):
                return FlagEvaluationResult.match(
                    value=flag.enabled_value,
                    reason="Custom rule matched",
                )
        except Exception as e:
            logger.warning(
                "custom_rule_evaluation_failed",
                exc_info=True,
                extra={
                    "flag_key": flag.key,
                    "user_id": context.user_id,
                    "error": str(e),
                    "operation": "FLAG_EVALUATION_ERROR",
                },
            )

        return FlagEvaluationResult.no_match()


# =============================================================================
# Targeting Strategies
# =============================================================================


class UserTargetingStrategy(EvaluationStrategy):
    """Strategy for user-specific targeting.

    Enables flag for specific user IDs.
    """

    @property
    def priority(self) -> int:
        return 10  # Targeting priority

    def evaluate(
        self,
        flag: FlagConfig,
        context: EvaluationContext,
    ) -> FlagEvaluationResult:
        """Check if user is explicitly targeted."""
        if context.user_id and context.user_id in flag.user_ids:
            return FlagEvaluationResult.match(
                value=flag.enabled_value,
                reason=f"User {context.user_id} targeted",
            )
        return FlagEvaluationResult.no_match()


class GroupTargetingStrategy(EvaluationStrategy):
    """Strategy for group-based targeting.

    Enables flag for users in specific groups.
    """

    @property
    def priority(self) -> int:
        return 11  # After user targeting

    def evaluate(
        self,
        flag: FlagConfig,
        context: EvaluationContext,
    ) -> FlagEvaluationResult:
        """Check if user's groups match flag groups."""
        if context.groups and flag.groups:
            matching = set(context.groups) & set(flag.groups)
            if matching:
                return FlagEvaluationResult.match(
                    value=flag.enabled_value,
                    reason=f"Group {list(matching)[0]} targeted",
                )
        return FlagEvaluationResult.no_match()


# =============================================================================
# Rollout Strategy
# =============================================================================


class PercentageRolloutStrategy(EvaluationStrategy):
    """Strategy for percentage-based rollout.

    Uses consistent hashing to deterministically assign users to rollout
    percentage buckets.
    """

    def __init__(self, seed: int = 0) -> None:
        """Initialize percentage rollout strategy.

        Args:
            seed: Random seed for consistent hashing.
        """
        self._seed = seed

    @property
    def priority(self) -> int:
        return 20  # Rollout priority

    def evaluate(
        self,
        flag: FlagConfig,
        context: EvaluationContext,
    ) -> FlagEvaluationResult:
        """Check if user is in percentage rollout."""
        if flag.status == FlagStatus.PERCENTAGE and flag.percentage > 0:
            if self._is_in_percentage(flag.key, context.user_id, flag.percentage):
                return FlagEvaluationResult.match(
                    value=flag.enabled_value,
                    reason=f"In {flag.percentage}% rollout",
                )
        return FlagEvaluationResult.no_match()

    def _is_in_percentage(
        self,
        flag_key: str,
        user_id: str | None,
        percentage: float,
    ) -> bool:
        """Check if user is in percentage rollout.

        Uses consistent hashing so same user always gets same result.

        Args:
            flag_key: Flag key.
            user_id: User ID.
            percentage: Rollout percentage (0-100).

        Returns:
            True if user is in rollout.
        """
        if percentage >= 100:
            return True
        if percentage <= 0:
            return False

        # Use consistent hashing (MD5 not for security, just distribution)
        hash_input = f"{flag_key}:{user_id or 'anonymous'}:{self._seed}"
        hash_value = int(
            hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest(), 16
        )
        bucket = hash_value % 100

        return bucket < percentage


# =============================================================================
# Fallback Strategy
# =============================================================================


class DefaultValueStrategy(EvaluationStrategy):
    """Fallback strategy that returns default value.

    Lowest priority - only used if no other strategy matched.
    """

    @property
    def priority(self) -> int:
        return 100  # Lowest priority (fallback)

    def evaluate(
        self,
        flag: FlagConfig,
        context: EvaluationContext,
    ) -> FlagEvaluationResult:
        """Always match with default value."""
        return FlagEvaluationResult.match(
            value=flag.default_value,
            reason="No matching rules",
        )


# =============================================================================
# Strategy Chain
# =============================================================================


class StrategyChain:
    """Chain of evaluation strategies.

    Evaluates strategies in priority order until first match.
    """

    def __init__(self, strategies: list[EvaluationStrategy] | None = None) -> None:
        """Initialize strategy chain.

        Args:
            strategies: List of strategies to evaluate.
        """
        self._strategies = strategies or []
        self._strategies.sort(key=lambda s: s.priority)

    def add_strategy(self, strategy: EvaluationStrategy) -> None:
        """Add strategy to chain.

        Args:
            strategy: Strategy to add.
        """
        self._strategies.append(strategy)
        self._strategies.sort(key=lambda s: s.priority)

    def remove_strategy(self, strategy_type: type[EvaluationStrategy]) -> bool:
        """Remove strategy from chain by type.

        Args:
            strategy_type: Type of strategy to remove.

        Returns:
            True if strategy was removed.
        """
        original_len = len(self._strategies)
        self._strategies = [s for s in self._strategies if not isinstance(s, strategy_type)]
        return len(self._strategies) < original_len

    def evaluate(
        self,
        flag: FlagConfig,
        context: EvaluationContext,
    ) -> tuple[Any, str]:
        """Evaluate flag using strategy chain.

        Args:
            flag: Flag configuration.
            context: Evaluation context.

        Returns:
            Tuple of (value, reason).
        """
        for strategy in self._strategies:
            result = strategy.evaluate(flag, context)
            if result.matched:
                logger.debug(
                    "flag_evaluation_matched",
                    extra={
                        "flag_key": flag.key,
                        "strategy": type(strategy).__name__,
                        "value": result.value,
                        "reason": result.reason,
                        "user_id": context.user_id,
                        "operation": "FLAG_EVALUATION",
                    },
                )
                return result.value, result.reason

        # Should never reach here if DefaultValueStrategy is in chain
        logger.warning(
            "flag_evaluation_no_match",
            extra={
                "flag_key": flag.key,
                "strategies_count": len(self._strategies),
                "operation": "FLAG_EVALUATION_WARNING",
            },
        )
        return flag.default_value, "No strategies matched"


# =============================================================================
# Factory Function
# =============================================================================


def create_default_strategy_chain(seed: int = 0) -> StrategyChain:
    """Create default strategy chain with standard strategies.

    Args:
        seed: Random seed for percentage rollout.

    Returns:
        Configured strategy chain.

    Example:
        >>> chain = create_default_strategy_chain()
        >>> value, reason = chain.evaluate(flag, context)
    """
    return StrategyChain(
        strategies=[
            DisabledStrategy(),           # Priority 0
            EnabledStrategy(),            # Priority 1
            CustomRuleStrategy(),         # Priority 5
            UserTargetingStrategy(),      # Priority 10
            GroupTargetingStrategy(),     # Priority 11
            PercentageRolloutStrategy(seed),  # Priority 20
            DefaultValueStrategy(),       # Priority 100 (fallback)
        ]
    )
