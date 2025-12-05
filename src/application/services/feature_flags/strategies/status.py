"""Status-based evaluation strategies.

**Feature: application-layer-code-review-2025**
**Refactored: Split from strategies.py for one-class-per-file compliance**
"""

from application.services.feature_flags.config import FlagConfig
from application.services.feature_flags.core import FlagStatus
from application.services.feature_flags.models import EvaluationContext
from application.services.feature_flags.core.base import (
    EvaluationStrategy,
    FlagEvaluationResult,
)


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


