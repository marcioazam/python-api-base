"""Base classes for feature flag evaluation strategies.

**Feature: application-layer-code-review-2025**
**Refactored: Split from strategies.py for one-class-per-file compliance**
"""

from abc import ABC, abstractmethod
from typing import Any

from application.services.feature_flags.config import FlagConfig
from application.services.feature_flags.models import EvaluationContext


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
