"""Feature flags service for controlled feature rollouts.

Provides feature flag management with percentage-based rollouts,
user targeting, and custom evaluation rules using Strategy pattern.

**Feature: application-layer-improvements-2025**
**Validates: Requirements 10.1, 10.2, 10.3, Strategy pattern refactoring**
"""

from .enums import FlagStatus, RolloutStrategy
from .models import EvaluationContext
from .config import FlagConfig
from .service import FeatureFlagService
from .strategies import (
    EvaluationStrategy,
    FlagEvaluationResult,
    StrategyChain,
    DisabledStrategy,
    EnabledStrategy,
    CustomRuleStrategy,
    UserTargetingStrategy,
    GroupTargetingStrategy,
    PercentageRolloutStrategy,
    DefaultValueStrategy,
    create_default_strategy_chain,
)

__all__ = [
    # Enums
    "FlagStatus",
    "RolloutStrategy",
    # Models
    "EvaluationContext",
    "FlagConfig",
    # Service
    "FeatureFlagService",
    # Strategies
    "EvaluationStrategy",
    "FlagEvaluationResult",
    "StrategyChain",
    "DisabledStrategy",
    "EnabledStrategy",
    "CustomRuleStrategy",
    "UserTargetingStrategy",
    "GroupTargetingStrategy",
    "PercentageRolloutStrategy",
    "DefaultValueStrategy",
    "create_default_strategy_chain",
]
