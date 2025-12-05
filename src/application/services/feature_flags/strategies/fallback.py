"""Fallback evaluation strategy.

**Feature: application-layer-code-review-2025**
**Refactored: Split from strategies.py for one-class-per-file compliance**
"""

from application.services.feature_flags.config import FlagConfig
from application.services.feature_flags.models import EvaluationContext
from application.services.feature_flags.core.base import (
    EvaluationStrategy,
    FlagEvaluationResult,
)


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


