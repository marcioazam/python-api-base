# ADR-005: Large File Refactoring

## Status
Accepted

## Context
Code review identified 15 files exceeding the 400-line limit established in project standards. Large files increase cognitive load, reduce maintainability, and violate Single Responsibility Principle (SRP).

**Files identified (>400 lines):**
- `query_builder.py` (562 lines)
- `batch.py` (581 lines)
- `event_sourcing.py` (522 lines)
- `oauth2.py` (454 lines)
- `cloud_provider_filter.py` (456 lines)
- `fuzzing.py` (453 lines)
- `contract_testing.py` (440 lines)
- `caching.py` (431 lines)
- `secrets_manager.py` (417 lines)
- `tiered_rate_limiter.py` (414 lines)
- And 5 others between 400-415 lines

## Decision
Refactor large modules into packages with focused sub-modules while maintaining backward compatibility through re-exports.

### Pattern Applied
```
src/my_api/shared/module.py (562 lines)
    ↓ refactored to
src/my_api/shared/module/
    __init__.py      (re-exports)
    types.py         (~100 lines)
    core.py          (~150 lines)
    implementation.py (~150 lines)
```

### Completed Refactoring

**1. query_builder.py → query_builder/**
- `conditions.py` - Enums, QueryCondition, SortClause, ConditionGroup
- `field_accessor.py` - FieldAccessor class and field_() factory
- `builder.py` - Abstract QueryBuilder base class
- `in_memory.py` - InMemoryQueryBuilder implementation

**2. batch.py → batch/**
- `config.py` - BatchConfig, BatchResult, BatchProgress, enums
- `repository.py` - IBatchRepository, BatchRepository, chunk utilities
- `builder.py` - BatchOperationBuilder fluent API

### Security Fix Applied
- `rate_limiter.py` - Added IP validation to prevent X-Forwarded-For spoofing

## Consequences

### Positive
- Files now comply with 400-line limit
- Improved code navigation and discoverability
- Better separation of concerns
- Easier unit testing of individual components
- Backward compatible via re-exports

### Negative
- More files to navigate
- Import paths slightly longer internally
- One-time migration effort

### Neutral
- External API unchanged
- No breaking changes for consumers

## Alternatives Considered

1. **Keep large files** - Rejected: violates standards, reduces maintainability
2. **Break backward compatibility** - Rejected: would require updates across codebase
3. **Partial refactoring** - Rejected: inconsistent approach

## References
- Project standards: Files 200-400 max 500 lines
- SOLID principles: Single Responsibility
- Python packaging best practices
