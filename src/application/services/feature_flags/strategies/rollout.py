"""Percentage rollout evaluation strategy.

**Feature: application-layer-code-review-2025**
**Refactored: Split from strategies.py for one-class-per-file compliance**
"""

import hashlib

from application.services.feature_flags.config import FlagConfig
from application.services.feature_flags.core import FlagStatus
from application.services.feature_flags.models import EvaluationContext
from application.services.feature_flags.core.base import (
    EvaluationStrategy,
    FlagEvaluationResult,
)


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
        is_percentage_rollout = flag.status == FlagStatus.PERCENTAGE and flag.percentage > 0
        if is_percentage_rollout and self._is_in_percentage(flag.key, context.user_id, flag.percentage):
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


