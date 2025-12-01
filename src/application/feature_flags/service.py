"""feature_flags service."""

import hashlib
from datetime import datetime, UTC
from typing import Any
from collections.abc import Callable
from pydantic import BaseModel
from .enums import FlagStatus
from .models import EvaluationContext
from .config import FlagConfig


class FlagEvaluation(BaseModel):
    """Result of flag evaluation.

    Attributes:
        flag_key: Flag key.
        value: Evaluated value.
        reason: Reason for the value.
        is_default: Whether default value was used.
    """

    flag_key: str
    value: Any
    reason: str
    is_default: bool = False

class FeatureFlagService:
    """Feature flag service.

    Provides feature flag management with:
    - Percentage-based rollouts
    - User targeting
    - Group targeting
    - Custom rules
    """

    def __init__(self, seed: int | None = None) -> None:
        """Initialize feature flag service.

        Args:
            seed: Random seed for consistent hashing.
        """
        self._flags: dict[str, FlagConfig] = {}
        self._custom_rules: dict[str, Callable[[EvaluationContext], bool]] = {}
        self._seed = seed or 0

    def register_flag(self, config: FlagConfig) -> None:
        """Register a feature flag.

        Args:
            config: Flag configuration.
        """
        self._flags[config.key] = config

    def unregister_flag(self, key: str) -> bool:
        """Unregister a feature flag.

        Args:
            key: Flag key.

        Returns:
            True if flag was removed.
        """
        if key in self._flags:
            del self._flags[key]
            return True
        return False

    def get_flag(self, key: str) -> FlagConfig | None:
        """Get flag configuration.

        Args:
            key: Flag key.

        Returns:
            Flag config or None.
        """
        return self._flags.get(key)

    def list_flags(self) -> list[FlagConfig]:
        """List all registered flags.

        Returns:
            List of flag configurations.
        """
        return list(self._flags.values())

    def set_custom_rule(
        self,
        flag_key: str,
        rule: Callable[[EvaluationContext], bool],
    ) -> None:
        """Set a custom evaluation rule for a flag.

        Args:
            flag_key: Flag key.
            rule: Custom rule function.
        """
        self._custom_rules[flag_key] = rule

    def is_enabled(
        self,
        key: str,
        context: EvaluationContext | None = None,
    ) -> bool:
        """Check if a flag is enabled.

        Args:
            key: Flag key.
            context: Evaluation context.

        Returns:
            True if flag is enabled.
        """
        evaluation = self.evaluate(key, context)
        return bool(evaluation.value)

    def evaluate(
        self,
        key: str,
        context: EvaluationContext | None = None,
    ) -> FlagEvaluation:
        """Evaluate a feature flag.

        Args:
            key: Flag key.
            context: Evaluation context.

        Returns:
            Flag evaluation result.
        """
        context = context or EvaluationContext()

        flag = self._flags.get(key)
        if not flag:
            return FlagEvaluation(
                flag_key=key,
                value=False,
                reason="Flag not found",
                is_default=True,
            )

        # Check status
        if flag.status == FlagStatus.DISABLED:
            return FlagEvaluation(
                flag_key=key,
                value=flag.default_value,
                reason="Flag disabled",
                is_default=True,
            )

        if flag.status == FlagStatus.ENABLED:
            return FlagEvaluation(
                flag_key=key,
                value=flag.enabled_value,
                reason="Flag enabled",
            )

        # Check custom rule
        if key in self._custom_rules:
            try:
                if self._custom_rules[key](context):
                    return FlagEvaluation(
                        flag_key=key,
                        value=flag.enabled_value,
                        reason="Custom rule matched",
                    )
            except Exception:
                pass

        # Check user targeting
        if context.user_id and context.user_id in flag.user_ids:
            return FlagEvaluation(
                flag_key=key,
                value=flag.enabled_value,
                reason=f"User {context.user_id} targeted",
            )

        # Check group targeting
        if context.groups:
            matching_groups = set(context.groups) & set(flag.groups)
            if matching_groups:
                return FlagEvaluation(
                    flag_key=key,
                    value=flag.enabled_value,
                    reason=f"Group {list(matching_groups)[0]} targeted",
                )

        # Check percentage rollout
        if flag.status == FlagStatus.PERCENTAGE and flag.percentage > 0:
            if self._is_in_percentage(key, context.user_id, flag.percentage):
                return FlagEvaluation(
                    flag_key=key,
                    value=flag.enabled_value,
                    reason=f"In {flag.percentage}% rollout",
                )

        return FlagEvaluation(
            flag_key=key,
            value=flag.default_value,
            reason="No matching rules",
            is_default=True,
        )

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
            percentage: Rollout percentage.

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

    def enable_flag(self, key: str) -> bool:
        """Enable a flag.

        Args:
            key: Flag key.

        Returns:
            True if flag was enabled.
        """
        flag = self._flags.get(key)
        if flag:
            flag.status = FlagStatus.ENABLED
            flag.updated_at = datetime.now(UTC)
            return True
        return False

    def disable_flag(self, key: str) -> bool:
        """Disable a flag.

        Args:
            key: Flag key.

        Returns:
            True if flag was disabled.
        """
        flag = self._flags.get(key)
        if flag:
            flag.status = FlagStatus.DISABLED
            flag.updated_at = datetime.now(UTC)
            return True
        return False

    def set_percentage(self, key: str, percentage: float) -> bool:
        """Set percentage rollout for a flag.

        Args:
            key: Flag key.
            percentage: Rollout percentage (0-100).

        Returns:
            True if percentage was set.
        """
        flag = self._flags.get(key)
        if flag:
            flag.status = FlagStatus.PERCENTAGE
            flag.percentage = max(0, min(100, percentage))
            flag.updated_at = datetime.now(UTC)
            return True
        return False

    def add_user_target(self, key: str, user_id: str) -> bool:
        """Add user to flag targeting.

        Args:
            key: Flag key.
            user_id: User ID to target.

        Returns:
            True if user was added.
        """
        flag = self._flags.get(key)
        if flag:
            if user_id not in flag.user_ids:
                flag.user_ids.append(user_id)
            flag.status = FlagStatus.TARGETED
            flag.updated_at = datetime.now(UTC)
            return True
        return False

    def remove_user_target(self, key: str, user_id: str) -> bool:
        """Remove user from flag targeting.

        Args:
            key: Flag key.
            user_id: User ID to remove.

        Returns:
            True if user was removed.
        """
        flag = self._flags.get(key)
        if flag and user_id in flag.user_ids:
            flag.user_ids.remove(user_id)
            flag.updated_at = datetime.now(UTC)
            return True
        return False

def create_flag(
    key: str,
    name: str = "",
    enabled: bool = False,
    percentage: float | None = None,
) -> FlagConfig:
    """Create a feature flag configuration.

    Args:
        key: Flag key.
        name: Flag name.
        enabled: Whether flag is enabled.
        percentage: Optional percentage rollout.

    Returns:
        Flag configuration.
    """
    status = FlagStatus.ENABLED if enabled else FlagStatus.DISABLED
    if percentage is not None:
        status = FlagStatus.PERCENTAGE

    return FlagConfig(
        key=key,
        name=name or key,
        status=status,
        percentage=percentage or 0.0,
    )
