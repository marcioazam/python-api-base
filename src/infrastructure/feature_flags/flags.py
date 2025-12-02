"""Generic feature flag support with PEP 695 type parameters.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 19.1, 19.2, 19.3, 19.4, 19.5**
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class FlagStatus(Enum):
    """Feature flag status."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    PERCENTAGE = "percentage"
    TARGETED = "targeted"


@dataclass(frozen=True, slots=True)
class EvaluationContext[TContext]:
    """Context for flag evaluation.

    Type Parameters:
        TContext: Type of user/request context.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 19.1**
    """

    user_id: str | None = None
    groups: tuple[str, ...] = ()
    attributes: dict[str, Any] = field(default_factory=dict)
    context_data: TContext | None = None


@dataclass
class FeatureFlag[TContext]:
    """Generic feature flag with typed evaluation context.

    Type Parameters:
        TContext: Type of evaluation context.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 19.1**
    """

    key: str
    name: str
    description: str = ""
    status: FlagStatus = FlagStatus.DISABLED
    percentage: float = 0.0  # 0-100 for percentage rollouts
    enabled_users: set[str] = field(default_factory=set)
    enabled_groups: set[str] = field(default_factory=set)
    disabled_users: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def is_enabled_for(self, context: EvaluationContext[TContext]) -> bool:
        """Check if flag is enabled for given context."""
        # Check explicit disable
        if context.user_id and context.user_id in self.disabled_users:
            return False

        # Check status
        if self.status == FlagStatus.DISABLED:
            return False

        if self.status == FlagStatus.ENABLED:
            return True

        # Check user targeting
        if context.user_id and context.user_id in self.enabled_users:
            return True

        # Check group targeting
        if self.status == FlagStatus.TARGETED:
            for group in context.groups:
                if group in self.enabled_groups:
                    return True
            return False

        # Percentage rollout
        if self.status == FlagStatus.PERCENTAGE and context.user_id:
            return self._check_percentage(context.user_id)

        return False

    def _check_percentage(self, user_id: str) -> bool:
        """Check percentage rollout using consistent hashing."""
        hash_input = f"{self.key}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = hash_value % 100
        return bucket < self.percentage


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Result of flag evaluation."""

    flag_key: str
    enabled: bool
    reason: str
    variant: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class FeatureFlagEvaluator[TContext]:
    """Generic feature flag evaluator with percentage rollouts.

    Type Parameters:
        TContext: Type of evaluation context.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 19.2**
    """

    def __init__(self, flags: dict[str, FeatureFlag[TContext]] | None = None) -> None:
        self._flags: dict[str, FeatureFlag[TContext]] = flags or {}

    def register(self, flag: FeatureFlag[TContext]) -> None:
        """Register a feature flag."""
        self._flags[flag.key] = flag

    def evaluate(
        self,
        flag_key: str,
        context: EvaluationContext[TContext],
    ) -> EvaluationResult:
        """Evaluate a feature flag.

        Args:
            flag_key: The flag key to evaluate.
            context: Evaluation context.

        Returns:
            EvaluationResult with enabled status and reason.
        """
        flag = self._flags.get(flag_key)
        if flag is None:
            return EvaluationResult(
                flag_key=flag_key,
                enabled=False,
                reason="FLAG_NOT_FOUND",
            )

        enabled = flag.is_enabled_for(context)
        reason = self._get_reason(flag, context, enabled)

        return EvaluationResult(
            flag_key=flag_key,
            enabled=enabled,
            reason=reason,
            metadata=flag.metadata,
        )

    def _get_reason(
        self,
        flag: FeatureFlag[TContext],
        context: EvaluationContext[TContext],
        enabled: bool,
    ) -> str:
        """Get evaluation reason."""
        if context.user_id and context.user_id in flag.disabled_users:
            return "USER_DISABLED"
        if flag.status == FlagStatus.DISABLED:
            return "FLAG_DISABLED"
        if flag.status == FlagStatus.ENABLED:
            return "FLAG_ENABLED"
        if context.user_id and context.user_id in flag.enabled_users:
            return "USER_TARGETED"
        if flag.status == FlagStatus.TARGETED:
            return "GROUP_TARGETED" if enabled else "NOT_IN_TARGET"
        if flag.status == FlagStatus.PERCENTAGE:
            return "PERCENTAGE_INCLUDED" if enabled else "PERCENTAGE_EXCLUDED"
        return "UNKNOWN"

    def is_enabled(
        self,
        flag_key: str,
        context: EvaluationContext[TContext],
    ) -> bool:
        """Quick check if flag is enabled."""
        return self.evaluate(flag_key, context).enabled


@runtime_checkable
class FeatureFlagStore[TProvider](Protocol):
    """Generic feature flag store protocol for multiple backends.

    Type Parameters:
        TProvider: Provider-specific configuration type.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 19.3**
    """

    async def get(self, key: str) -> FeatureFlag[Any] | None:
        """Get feature flag by key."""
        ...

    async def get_all(self) -> list[FeatureFlag[Any]]:
        """Get all feature flags."""
        ...

    async def save(self, flag: FeatureFlag[Any]) -> None:
        """Save or update feature flag."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete feature flag by key."""
        ...


class InMemoryFeatureFlagStore[TContext]:
    """In-memory feature flag store.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 19.3**
    """

    def __init__(self) -> None:
        self._flags: dict[str, FeatureFlag[TContext]] = {}

    async def get(self, key: str) -> FeatureFlag[TContext] | None:
        """Get feature flag by key."""
        return self._flags.get(key)

    async def get_all(self) -> list[FeatureFlag[TContext]]:
        """Get all feature flags."""
        return list(self._flags.values())

    async def save(self, flag: FeatureFlag[TContext]) -> None:
        """Save or update feature flag."""
        self._flags[flag.key] = flag

    async def delete(self, key: str) -> bool:
        """Delete feature flag by key."""
        if key in self._flags:
            del self._flags[key]
            return True
        return False


@dataclass(frozen=True, slots=True)
class FlagEvaluationLog:
    """Audit log for flag evaluations.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 19.5**
    """

    flag_key: str
    user_id: str | None
    result: bool
    reason: str
    timestamp: datetime
    context_attributes: dict[str, Any]


class FlagAuditLogger:
    """Logger for flag evaluation auditing.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 19.5**
    """

    def __init__(self) -> None:
        self._logs: list[FlagEvaluationLog] = []

    def log_evaluation(
        self,
        result: EvaluationResult,
        context: EvaluationContext[Any],
    ) -> None:
        """Log flag evaluation."""
        log_entry = FlagEvaluationLog(
            flag_key=result.flag_key,
            user_id=context.user_id,
            result=result.enabled,
            reason=result.reason,
            timestamp=datetime.now(),
            context_attributes=context.attributes,
        )
        self._logs.append(log_entry)
        logger.debug(
            f"Flag '{result.flag_key}' evaluated: {result.enabled} ({result.reason})"
        )

    def get_logs(self, flag_key: str | None = None) -> list[FlagEvaluationLog]:
        """Get evaluation logs, optionally filtered by flag key."""
        if flag_key:
            return [log for log in self._logs if log.flag_key == flag_key]
        return list(self._logs)
