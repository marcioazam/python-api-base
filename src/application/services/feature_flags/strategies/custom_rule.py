"""Custom rule evaluation strategy.

**Feature: application-layer-code-review-2025**
**Refactored: Split from strategies.py for one-class-per-file compliance**
"""

import logging
from collections.abc import Callable

from application.services.feature_flags.config import FlagConfig
from application.services.feature_flags.models import EvaluationContext
from application.services.feature_flags.core.base import (
    EvaluationStrategy,
    FlagEvaluationResult,
)

logger = logging.getLogger(__name__)


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


