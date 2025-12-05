# ADR-017: Middleware, Mixins, Services, and Use Cases Restructuring

**Status:** Accepted  
**Date:** 2025-12-05  
**Deciders:** Architecture Team

## Context

The `src/application/common/` module contained four directories with flat or partially organized structures:

- **middleware/** - 13 files with mixed responsibilities (cache, resilience, observability, operations, validation)
- **mixins/** - 1 file (event publishing mixin)
- **services/** - 2 files (cache service, Kafka event service)
- **use_cases/** - 1 file (base use case)

This flat structure made it difficult to navigate and understand the organization by responsibility.

## Decision

Reorganize each directory into responsibility-separated subpackages:

### 1. **middleware/** → Organized by cross-cutting concern

```text
middleware/
├── cache/                    # Query caching and cache invalidation
│   ├── cache_invalidation.py
│   ├── query_cache.py
│   └── __init__.py
├── resilience/               # Retry, circuit breaker, resilience
│   ├── circuit_breaker.py
│   ├── retry.py
│   ├── resilience.py
│   └── __init__.py
├── observability/            # Logging, metrics, idempotency
│   ├── logging_middleware.py
│   ├── metrics_middleware.py
│   ├── observability.py
│   └── __init__.py
├── operations/               # Transaction management
│   ├── idempotency_middleware.py
│   ├── transaction.py
│   └── __init__.py
├── validation/               # Command validation
│   ├── validation.py
│   ├── middleware.py
│   └── __init__.py
└── __init__.py               # Façade
```

### 2. **mixins/** → Organized by feature

```text
mixins/
├── event_publishing/         # Event publishing mixin
│   ├── event_publishing.py
│   └── __init__.py
└── __init__.py               # Façade
```

### 3. **services/** → Organized by service type

```text
services/
├── cache/                    # Cache service
│   ├── cache_service.py
│   └── __init__.py
├── events/                   # Event services
│   ├── kafka_event_service.py
│   └── __init__.py
└── __init__.py               # Façade
```

### 4. **use_cases/** → Organized by responsibility

```text
use_cases/
├── base/                     # Base use case classes
│   ├── use_case.py
│   └── __init__.py
└── __init__.py               # Façade
```

## Rationale

1. **Separation of Concerns**: Each subpackage groups related functionality by responsibility
2. **Scalability**: Easier to add new features to specific areas without cluttering the main directory
3. **Discoverability**: Clear structure helps developers find relevant code quickly
4. **Maintainability**: Reduces cognitive load when working with specific patterns
5. **Backward Compatibility**: Public API remains unchanged via façade `__init__.py` files
6. **One Class Per File**: Follows Python best practices for file organization

## Consequences

### Positive

- Clear responsibility separation within each module
- Easier to locate and modify specific components
- Better organized for future extensions
- Improved code navigation and IDE support
- Maintains full backward compatibility
- Follows Python best practices

### Negative

- More files to manage (increased file count)
- Developers need to understand the new structure
- Slightly deeper import paths for internal use

### Neutral

- No performance impact
- No API changes for consumers
- No breaking changes

## Implementation Details

### File Movements

- **middleware/**: 10 files moved into 5 subpackages (cache, resilience, observability, operations, validation)
- **mixins/**: 1 file moved into event_publishing subpackage
- **services/**: 2 files moved into cache and events subpackages
- **use_cases/**: 1 file moved into base subpackage

### Import Updates

- All internal imports updated to reflect new paths
- All `__init__.py` files created with proper re-exports
- Public API maintained through façade pattern
- All external imports continue to work unchanged

### Code Improvements

1. **Improved Organization**: Middleware organized by cross-cutting concern
2. **Better Discoverability**: Clear separation of cache, resilience, observability, and operations
3. **Maintained Compatibility**: Façade pattern ensures no breaking changes
4. **Type Safety**: All imports properly typed and validated

## Validation

All imports tested and verified:

```python
from application.common.middleware import (
    CacheInvalidationStrategy, InMemoryQueryCache,
    CircuitBreakerConfig, RetryConfig,
    LoggingMiddleware, MetricsMiddleware,
    TransactionMiddleware, IdempotencyMiddleware,
    ValidationMiddleware
)
from application.common.mixins import EventPublishingMixin
from application.common.services import CacheService, KafkaEventService
from application.common.use_cases import BaseUseCase
```

## Related ADRs

- ADR-016: Application Common Module Restructuring
- ADR-015: CQRS Module Restructuring
- ADR-014: API Best Practices 2025

## References

- **Feature**: `architecture-restructuring-2025`
- **Pattern**: Façade Pattern for backward compatibility
- **Best Practice**: One class per file organization
