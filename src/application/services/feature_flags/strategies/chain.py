"""Strategy chain for feature flag evaluation.

**Feature: application-layer-code-review-2025**
**Refactored: Split from strategies.py for one-class-per-file compliance**
"""

import logging
from typing import Any

from application.services.feature_flags.config import FlagConfig
from application.services.feature_flags.models import EvaluationContext
from application.services.feature_flags.core.base import EvaluationStrategy
from application.services.feature_flags.strategies.custom_rule import CustomRuleStrategy
from application.services.feature_flags.strategies.fallback import DefaultValueStrategy
from application.services.feature_flags.strategies.rollout import PercentageRolloutStrategy
from application.services.feature_flags.strategies.status import DisabledStrategy, EnabledStrategy
from application.services.feature_flags.strategies.targeting import (
    GroupTargetingStrategy,
    UserTargetingStrategy,
)

logger = logging.getLogger(__name__)


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
        self._strategies = [
            s for s in self._strategies if not isinstance(s, strategy_type)
        ]
        return len(self._strategies) < original_len

    def get_strategies(self) -> list[EvaluationStrategy]:
        """Get list of strategies (read-only access).

        Returns:
            Copy of strategies list.
        """
        return list(self._strategies)

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
            DisabledStrategy(),  # Priority 0
            EnabledStrategy(),  # Priority 1
            CustomRuleStrategy(),  # Priority 5
            UserTargetingStrategy(),  # Priority 10
            GroupTargetingStrategy(),  # Priority 11
            PercentageRolloutStrategy(seed),  # Priority 20
            DefaultValueStrategy(),  # Priority 100 (fallback)
        ]
    )

