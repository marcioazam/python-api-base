# Design Document: Generics 100% Fixes

## Overview

Este documento detalha as correções necessárias para atingir 100% de conformidade com PEP 695 Generics no codebase Python API Base. São 4 issues pontuais identificados na análise anterior.

## Architecture

As correções são localizadas e não alteram a arquitetura geral:

```
src/
├── infrastructure/
│   ├── db/repositories/
│   │   └── sqlmodel_repository.py  # Fix: Add IdType generic
│   └── i18n/
│       └── generics.py             # Fix: Complete truncated file
├── application/common/
│   └── bus.py                      # Fix: Remove Middleware duplication
└── core/di/
    └── container.py                # Fix: Add error handling
```

## Components and Interfaces

### 1. SQLModelRepository with IdType

```python
class SQLModelRepository[
    T: SQLModel,
    CreateT: BaseModel,
    UpdateT: BaseModel,
    IdType: (str, int) = str,
](IRepository[T, CreateT, UpdateT, IdType]):
    """SQLModel repository with full generic support."""
    
    async def get_by_id(self, id: IdType) -> T | None: ...
    async def bulk_delete(self, ids: Sequence[IdType], *, soft: bool = True) -> int: ...
    async def bulk_update(self, updates: Sequence[tuple[IdType, UpdateT]]) -> Sequence[T]: ...
```

### 2. i18n Generic Infrastructure

```python
@runtime_checkable
class Translator[TKey](Protocol):
    """Protocol for typed translation."""
    def translate(self, key: TKey, locale: Locale) -> str: ...

@dataclass(frozen=True, slots=True)
class LocalizedValue[T]:
    """Value with locale information."""
    value: T
    locale: Locale

class MessageFormatter[T](Protocol):
    """Protocol for typed message formatting."""
    def format(self, template: str, values: T) -> str: ...

class PluralRules[T](Protocol):
    """Protocol for plural form selection."""
    def select(self, count: int, forms: dict[str, T]) -> T: ...

class TranslationCatalog[TKey]:
    """Type-safe translation catalog."""
    def get(self, key: TKey, locale: Locale) -> str | None: ...
    def get_or_default(self, key: TKey, locale: Locale, default: str) -> str: ...
```

### 3. Middleware Type Fix

```python
# BEFORE (conflicting):
@runtime_checkable
class Middleware[TCommand, TResult](Protocol): ...
Middleware = Callable[[Any, Callable[..., Any]], Any]  # Conflict!

# AFTER (clean):
@runtime_checkable
class Middleware[TCommand, TResult](Protocol):
    """Protocol for typed command middleware."""
    async def __call__(
        self,
        command: TCommand,
        next_handler: Callable[[TCommand], Awaitable[TResult]],
    ) -> TResult: ...

# Type alias with different name
MiddlewareFunc = Callable[[Any, Callable[..., Any]], Awaitable[Any]]
```

### 4. Container Error Handling

```python
class DependencyResolutionError(Exception):
    """Raised when dependency cannot be resolved."""
    def __init__(self, service_type: type, param_name: str, expected_type: type) -> None:
        self.service_type = service_type
        self.param_name = param_name
        self.expected_type = expected_type
        super().__init__(
            f"Cannot resolve parameter '{param_name}' of type '{expected_type.__name__}' "
            f"for service '{service_type.__name__}'"
        )

class CircularDependencyError(Exception):
    """Raised when circular dependency is detected."""
    def __init__(self, chain: list[type]) -> None:
        self.chain = chain
        chain_str = " -> ".join(t.__name__ for t in chain)
        super().__init__(f"Circular dependency detected: {chain_str}")
```

## Data Models

### LocalizedValue

```python
@dataclass(frozen=True, slots=True)
class LocalizedValue[T]:
    """Value with locale information."""
    value: T
    locale: Locale
    
    def with_locale(self, locale: Locale) -> "LocalizedValue[T]":
        """Create copy with different locale."""
        return LocalizedValue(value=self.value, locale=locale)
```

### TranslationEntry

```python
@dataclass(frozen=True, slots=True)
class TranslationEntry[TKey]:
    """Entry in translation catalog."""
    key: TKey
    locale: Locale
    value: str
    plural_forms: dict[str, str] | None = None
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Repository IdType Consistency
*For any* SQLModelRepository[T, CreateT, UpdateT, IdType], all ID operations (get_by_id, bulk_delete, bulk_update) should accept and return the same IdType.
**Validates: Requirements 1.2, 1.3, 1.4**

### Property 2: LocalizedValue Round-Trip
*For any* value T and locale, creating LocalizedValue[T] and accessing value should return the original value unchanged.
**Validates: Requirements 2.3**

### Property 3: MessageFormatter Placeholder Substitution
*For any* template with N placeholders and N values, formatting should produce a string with all placeholders replaced.
**Validates: Requirements 2.2**

### Property 4: PluralRules Selection
*For any* count and plural forms dict, select should return a value from the dict based on locale-specific rules.
**Validates: Requirements 2.4**

### Property 5: TranslationCatalog Lookup
*For any* registered key and locale, get should return the registered translation.
**Validates: Requirements 2.5**

### Property 6: Middleware Type Preservation
*For any* middleware chain, type information should flow correctly from input to output.
**Validates: Requirements 3.4**

### Property 7: DependencyResolutionError Contains Info
*For any* unresolvable dependency, the error should contain service_type, param_name, and expected_type.
**Validates: Requirements 4.1, 4.4**

### Property 8: CircularDependencyError Contains Chain
*For any* circular dependency, the error should contain the complete dependency chain.
**Validates: Requirements 4.2**

### Property 9: Optional Dependency Handling
*For any* service with Optional[T] dependency where T is not registered, resolution should succeed with None.
**Validates: Requirements 4.3**

## Error Handling

### New Error Types

```python
class DependencyResolutionError(Exception):
    """Raised when dependency cannot be resolved."""
    service_type: type
    param_name: str
    expected_type: type

class CircularDependencyError(Exception):
    """Raised when circular dependency is detected."""
    chain: list[type]

class InvalidFactoryError(Exception):
    """Raised when factory signature is invalid."""
    factory: Callable
    reason: str
```

## Testing Strategy

### Property-Based Testing Framework

- **Library**: Hypothesis (Python)
- **Minimum iterations**: 100 per property
- **Annotation format**: `**Feature: generics-100-percent-fixes, Property {number}: {property_text}**`

### Test Structure

```
tests/
├── properties/
│   └── test_generics_100_percent_fixes_properties.py
└── unit/
    ├── test_sqlmodel_repository_idtype.py
    ├── test_i18n_generics.py
    ├── test_middleware_types.py
    └── test_container_errors.py
```

### Example Property Tests

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1), st.sampled_from([EN_US, PT_BR]))
def test_localized_value_round_trip(value: str, locale: Locale):
    """
    **Feature: generics-100-percent-fixes, Property 2: LocalizedValue Round-Trip**
    **Validates: Requirements 2.3**
    """
    localized = LocalizedValue(value=value, locale=locale)
    assert localized.value == value
    assert localized.locale == locale

@given(st.text(min_size=1))
def test_dependency_resolution_error_contains_info(param_name: str):
    """
    **Feature: generics-100-percent-fixes, Property 7: DependencyResolutionError Contains Info**
    **Validates: Requirements 4.1, 4.4**
    """
    error = DependencyResolutionError(
        service_type=MyService,
        param_name=param_name,
        expected_type=MyDependency,
    )
    assert param_name in str(error)
    assert "MyService" in str(error)
    assert "MyDependency" in str(error)
```

## Implementation Notes

### SQLModelRepository Changes

1. Add `IdType: (str, int) = str` as fourth type parameter
2. Update `get_by_id(self, id: IdType)` signature
3. Update `bulk_delete(self, ids: Sequence[IdType])` signature
4. Update `bulk_update(self, updates: Sequence[tuple[IdType, UpdateT]])` signature
5. Ensure inheritance matches `IRepository[T, CreateT, UpdateT, IdType]`

### i18n/generics.py Completion

1. Complete `Locale` class (already started)
2. Add common locale constants (EN_US, EN_GB, PT_BR, ES_ES, etc.)
3. Implement `Translator[TKey]` protocol
4. Implement `MessageFormatter[T]` protocol
5. Implement `LocalizedValue[T]` dataclass
6. Implement `PluralRules[T]` protocol
7. Implement `TranslationCatalog[TKey]` class
8. Add `NumberFormatter[T]` and `DateFormatter` utilities

### bus.py Middleware Fix

1. Keep `Middleware[TCommand, TResult](Protocol)` as the primary definition
2. Rename type alias to `MiddlewareFunc` to avoid conflict
3. Update `CommandBus._middleware` type annotation
4. Ensure all middleware references use the Protocol

### Container Error Handling

1. Add `DependencyResolutionError` exception class
2. Add `CircularDependencyError` exception class
3. Add `InvalidFactoryError` exception class
4. Implement circular dependency detection in `_create_instance`
5. Handle `Optional[T]` type hints specially
6. Improve error messages with full context
