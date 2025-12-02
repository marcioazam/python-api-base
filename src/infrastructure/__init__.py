"""Infrastructure layer - Adapters and external integrations.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 6-22**

Provides production-ready infrastructure components:
- audit: Audit trail with AuditRecord[T], AuditStore[TProvider]
- cache: Caching with CacheProvider[T], @cached decorator
- feature_flags: Feature flags with FeatureFlag[TContext]
- multitenancy: Multi-tenant support with TenantContext[TId]
- resilience: Resilience patterns with CircuitBreaker[TConfig], Retry[T]
- storage: File storage with FileUploadHandler[TMetadata]
"""

from infrastructure.audit import (
    AuditAction,
    AuditQuery,
    AuditRecord,
    AuditStore,
    InMemoryAuditStore,
)
from infrastructure.feature_flags import (
    EvaluationContext,
    FeatureFlag,
    FeatureFlagEvaluator,
    FlagStatus,
    InMemoryFeatureFlagStore,
)
from infrastructure.multitenancy import (
    TenantContext,
    TenantInfo,
    TenantResolutionStrategy,
)
from infrastructure.resilience import (
    Bulkhead,
    CircuitBreaker,
    CircuitBreakerConfig,
    Fallback,
    Retry,
    RetryConfig,
    Timeout,
    TimeoutConfig,
)
from infrastructure.storage import (
    FileInfo,
    FileStorage,
    FileUploadHandler,
    FileValidator,
)

__all__ = [
    # Audit
    "AuditAction",
    "AuditQuery",
    "AuditRecord",
    "AuditStore",
    "InMemoryAuditStore",
    # Feature Flags
    "EvaluationContext",
    "FeatureFlag",
    "FeatureFlagEvaluator",
    "FlagStatus",
    "InMemoryFeatureFlagStore",
    # Multitenancy
    "TenantContext",
    "TenantInfo",
    "TenantResolutionStrategy",
    # Resilience
    "Bulkhead",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "Fallback",
    "Retry",
    "RetryConfig",
    "Timeout",
    "TimeoutConfig",
    # Storage
    "FileInfo",
    "FileStorage",
    "FileUploadHandler",
    "FileValidator",
]
