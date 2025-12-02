"""Feature flags module.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 19.1-19.5**
"""

from .flags import (
    EvaluationContext,
    EvaluationResult,
    FeatureFlag,
    FeatureFlagEvaluator,
    FeatureFlagStore,
    FlagAuditLogger,
    FlagEvaluationLog,
    FlagStatus,
    InMemoryFeatureFlagStore,
)

__all__ = [
    "EvaluationContext",
    "EvaluationResult",
    "FeatureFlag",
    "FeatureFlagEvaluator",
    "FeatureFlagStore",
    "FlagAuditLogger",
    "FlagEvaluationLog",
    "FlagStatus",
    "InMemoryFeatureFlagStore",
]
