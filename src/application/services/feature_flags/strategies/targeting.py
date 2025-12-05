"""Targeting evaluation strategies.

**Feature: application-layer-code-review-2025**
**Refactored: Split from strategies.py for one-class-per-file compliance**
"""

from application.services.feature_flags.config import FlagConfig
from application.services.feature_flags.models import EvaluationContext
from application.services.feature_flags.core.base import (
    EvaluationStrategy,
    FlagEvaluationResult,
)


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
                    reason=f"Group {next(iter(matching))} targeted",
                )
        return FlagEvaluationResult.no_match()


