"""Feature flag evaluation strategies.

Re-exports all strategy classes for backward compatibility.

**Feature: application-layer-code-review-2025**
**Refactored: Split into separate files for one-class-per-file compliance**
"""

from application.services.feature_flags.core.base import (
    EvaluationStrategy,
    FlagEvaluationResult,
)
from application.services.feature_flags.strategies.chain import (
    StrategyChain,
    create_default_strategy_chain,
)
from application.services.feature_flags.strategies.custom_rule import CustomRuleStrategy
from application.services.feature_flags.strategies.fallback import DefaultValueStrategy
from application.services.feature_flags.strategies.rollout import PercentageRolloutStrategy
from application.services.feature_flags.strategies.status import DisabledStrategy, EnabledStrategy
from application.services.feature_flags.strategies.targeting import (
    GroupTargetingStrategy,
    UserTargetingStrategy,
)

__all__ = [
    # Base
    "EvaluationStrategy",
    "FlagEvaluationResult",
    # Status strategies
    "DisabledStrategy",
    "EnabledStrategy",
    # Custom rule
    "CustomRuleStrategy",
    # Targeting
    "UserTargetingStrategy",
    "GroupTargetingStrategy",
    # Rollout
    "PercentageRolloutStrategy",
    # Fallback
    "DefaultValueStrategy",
    # Chain
    "StrategyChain",
    "create_default_strategy_chain",
]

