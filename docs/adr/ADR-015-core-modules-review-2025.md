# ADR-015: Core Modules Review and Improvements (2025)

**Status:** Accepted  
**Date:** 2025-12-05  
**Author:** Architecture Review Team

## Context

Conducted comprehensive code review of three core modules (`core/di`, `core/protocols`, `core/types`) to validate structure, apply best practices, and identify improvement opportunities.

## Decision

### 1. **No Reorganization Required**

All three modules are **already well-organized** by responsibility. Each file has a clear, focused purpose:

#### core/di (Dependency Injection)
- `container.py` - Main Container orchestrator
- `exceptions.py` - 4 specific DI exceptions
- `lifecycle.py` - Lifetime enum and Registration dataclass
- `resolver.py` - Dependency resolution logic
- `scopes.py` - Scope management for scoped dependencies
- `metrics.py` - Observability and metrics tracking

**Verdict:** ✅ No subpastas needed. Structure is optimal.

#### core/protocols (Protocol Definitions)
- `base.py` - Base protocols (Identifiable, Timestamped, SoftDeletable)
- `application.py` - Application patterns (EventHandler, Command, Query, Mapper)
- `data_access.py` - Data access patterns (AsyncRepository, CacheProvider, UnitOfWork)
- `entities.py` - Entity protocols (Entity, TrackedEntity, VersionedEntity)
- `repository.py` - Repository patterns (AsyncRepository, CommandHandler, QueryHandler)

**Verdict:** ✅ No subpastas needed. Already grouped by domain.

#### core/types (Type Aliases)
- `id_types.py` - ID types (ULID, UUID, UUID7, EntityId)
- `json_types.py` - JSON types (JSONValue, JSONObject, JSONArray)
- `numeric_types.py` - Numeric types (PositiveInt, PageSize, Percentage)
- `repository_types.py` - Repository types (CRUDRepository, ReadOnlyRepository)
- `result_types.py` - Result pattern types (Success, Failure, OperationResult)
- `security_types.py` - Security types (JWTToken, Password, SecurePassword)
- `string_types.py` - String types (Email, Slug, URL, etc)

**Verdict:** ✅ No subpastas needed. Already grouped by category.

### 2. **Improvements Applied**

#### core/di/container.py
**Added:** `clear_singletons()` method for testing
- Clears all singleton instances without removing registrations
- Useful for ensuring clean state between tests
- Triggers observability hook `on_singletons_cleared`

```python
def clear_singletons(self) -> None:
    """Clear all singleton instances.
    
    Useful for testing to ensure clean state between tests.
    Does not remove registrations, only cached instances.
    """
    self._singletons.clear()
    self._metrics_tracker.trigger_hook(
        "on_singletons_cleared",
        count=len(self._singletons),
    )
```

#### core/types/string_types.py
**Added:** `URLPath` type for URL path validation
- Validates URL path components (e.g., `/api/v1/users`)
- Supports RFC 3986 unreserved and reserved characters
- Max length: 2048 characters

```python
URLPath = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=2048,
        pattern=r"^/[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]*$",
    ),
    Field(description="URL path component (e.g., /api/v1/users)"),
]
```

#### core/types/numeric_types.py
**Added:** `PercentageRange` type for range queries
- Tuple of (min, max) percentages
- Useful for filtering by percentage ranges
- Validates 0 <= min <= max <= 100

```python
PercentageRange = Annotated[
    tuple[float, float],
    Field(description="Percentage range as tuple (min, max) where 0 <= min <= max <= 100"),
]
```

## Consequences

### Positive
- ✅ Modules maintain clean separation of concerns
- ✅ No unnecessary complexity from subpastas
- ✅ Improved testability with `clear_singletons()`
- ✅ Enhanced type system with `URLPath` and `PercentageRange`
- ✅ All imports validated and working correctly
- ✅ Code compiles without errors

### Neutral
- No breaking changes to existing APIs
- All exports remain backward compatible

## Validation

### Code Quality Metrics
| Module | Status | Details |
|--------|--------|---------|
| **core/di** | ✅ | PEP 695 generics, type-safe, proper error handling |
| **core/protocols** | ✅ | Runtime checkable, PEP 695 type parameters |
| **core/types** | ✅ | PEP 593 Annotated, PEP 695 type aliases |

### Testing
- ✅ All modules compile without errors
- ✅ All imports work correctly
- ✅ No circular dependencies detected
- ✅ Type hints validated

## Alternatives Considered

1. **Reorganize into subpastas** - Rejected: Would add unnecessary complexity without clear benefit
2. **Rename files** - Rejected: Current names clearly reflect content
3. **Merge modules** - Rejected: Would violate SRP and reduce maintainability

## Related ADRs

- ADR-013: SQLModel Production Readiness
- ADR-014: API Best Practices 2025

## References

- PEP 695: Type Parameter Syntax
- PEP 593: Flexible Function and Variable Annotations
- Python Protocols: https://docs.python.org/3/library/typing.html#protocols
