# Design Document: Python API Base 2025 Generics Audit

## Overview

This design document specifies the architecture and implementation details for auditing and improving the Python API Base 2025 project. The focus is on maximizing the use of Python Generics (PEP 695), eliminating code duplication, and ensuring the codebase represents a state-of-the-art API framework.

The current implementation already demonstrates excellent use of generics. This audit validates the architecture and identifies opportunities for further improvement.

## Architecture

### Current Architecture Analysis

The project follows Clean Architecture with Hexagonal (Ports and Adapters) patterns:

```
src/
├── core/           # Core Layer - Framework-agnostic base classes
│   ├── base/       # Generic base classes (Entity, Repository, UseCase, Result)
│   ├── config/     # Configuration with Pydantic Settings
│   ├── di/         # Dependency Injection container
│   ├── errors/     # Error hierarchy
│   ├── protocols/  # Core protocols (Repository, UoW, Cache)
│   ├── shared/     # Shared utilities
│   └── types/      # Type definitions (PEP 695)
│
├── domain/         # Domain Layer - Business entities and rules
│   ├── common/     # Shared domain components
│   ├── items/      # Items aggregate
│   └── users/      # Users aggregate
│
├── application/    # Application Layer - Use cases and DTOs
│   ├── common/     # Generic DTOs, mappers, use cases
│   ├── items/      # Items use cases
│   ├── users/      # Users use cases
│   └── services/   # Cross-cutting services
│
├── infrastructure/ # Infrastructure Layer - External adapters
│   ├── auth/       # JWT, token store
│   ├── cache/      # Redis, in-memory cache
│   ├── db/         # SQLAlchemy, repositories
│   ├── generics/   # Generic infrastructure protocols
│   ├── messaging/  # Event bus, queues
│   ├── observability/ # Logging, tracing, metrics
│   └── security/   # Rate limiting, RBAC
│
└── interface/      # Interface Layer - API adapters
    ├── v1/         # API v1 routes
    ├── v2/         # API v2 routes
    └── middleware/ # HTTP middleware
```

### Architecture Conformance

| Layer | Status | Generic Usage |
|-------|--------|---------------|
| Core | ✅ Excellent | PEP 695 throughout |
| Domain | ✅ Good | BaseEntity[IdType] |
| Application | ✅ Excellent | BaseUseCase[T, CreateDTO, UpdateDTO, ResponseDTO] |
| Infrastructure | ✅ Excellent | SQLModelRepository[T, CreateT, UpdateT, IdType] |
| Interface | ✅ Good | GenericCRUDRouter[T, CreateDTO, UpdateDTO, ResponseDTO] |

## Components and Interfaces

### 1. Generic Repository Interface

```python
# src/core/base/repository_interface.py
class IRepository[T: BaseModel, CreateT: BaseModel, UpdateT: BaseModel, IdType: (str, int) = str](ABC):
    """Generic repository interface with PEP 695 syntax."""
    
    async def get_by_id(self, id: IdType) -> T | None: ...
    async def get_all(self, *, skip: int, limit: int, filters: dict | None, sort_by: str | None, sort_order: str) -> tuple[Sequence[T], int]: ...
    async def create(self, data: CreateT) -> T: ...
    async def update(self, id: IdType, data: UpdateT) -> T | None: ...
    async def delete(self, id: IdType, *, soft: bool = True) -> bool: ...
    async def create_many(self, data: Sequence[CreateT]) -> Sequence[T]: ...
    async def exists(self, id: IdType) -> bool: ...
    async def get_page(self, cursor: str | None, limit: int, filters: dict | None) -> CursorPage[T, str]: ...
```

### 2. Generic Use Case

```python
# src/core/base/use_case.py
class BaseUseCase[T: BaseModel, CreateDTO: BaseModel, UpdateDTO: BaseModel, ResponseDTO: BaseModel]:
    """Generic use case with CRUD operations and @overload for type narrowing."""
    
    @overload
    async def get(self, id: str, *, raise_on_missing: Literal[True] = True) -> ResponseDTO: ...
    @overload
    async def get(self, id: str, *, raise_on_missing: Literal[False]) -> ResponseDTO | None: ...
    
    async def list(self, *, page: int, size: int, filters: dict | None, sort_by: str | None, sort_order: str) -> PaginatedResponse[ResponseDTO]: ...
    async def create(self, data: CreateDTO) -> ResponseDTO: ...
    async def update(self, id: str, data: UpdateDTO) -> ResponseDTO: ...
    async def delete(self, id: str) -> bool: ...
```

### 3. Generic Result Pattern

```python
# src/core/base/result.py
@dataclass(frozen=True, slots=True)
class Ok[T]:
    value: T
    def map[U](self, fn: Callable[[T], U]) -> Ok[U]: ...
    def bind[U, F](self, fn: Callable[[T], Result[U, F]]) -> Result[U, F]: ...
    def and_then[U, F](self, fn: Callable[[T], Result[U, F]]) -> Result[U, F]: ...

@dataclass(frozen=True, slots=True)
class Err[E]:
    error: E
    def map_err[U](self, fn: Callable[[E], U]) -> Err[U]: ...
    def or_else[T, F](self, fn: Callable[[E], Result[T, F]]) -> Result[T, F]: ...

type Result[T, E] = Ok[T] | Err[E]
```

### 4. Generic Entity Hierarchy

```python
# src/core/base/entity.py
class BaseEntity[IdType: (str, int)](BaseModel):
    id: IdType | None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

class AuditableEntity[IdType: (str, int)](BaseEntity[IdType]):
    created_by: str | None
    updated_by: str | None

class VersionedEntity[IdType: (str, int), VersionT: (int, str) = int](BaseEntity[IdType]):
    version: VersionT

class AuditableVersionedEntity[IdType: (str, int), VersionT: (int, str) = int](AuditableEntity[IdType]):
    version: VersionT
```

### 5. Generic Infrastructure Protocols

```python
# src/infrastructure/generics/protocols.py
@runtime_checkable
class Repository[TEntity, TId](Protocol):
    def get(self, id: TId) -> TEntity | None: ...
    def get_all(self) -> list[TEntity]: ...
    def create(self, entity: TEntity) -> TEntity: ...
    def update(self, entity: TEntity) -> TEntity: ...
    def delete(self, id: TId) -> bool: ...

@runtime_checkable
class Service[TInput, TOutput, TError](Protocol):
    def execute(self, input: TInput) -> Result[TOutput, TError]: ...

@runtime_checkable
class Factory[TConfig, TInstance](Protocol):
    def create(self, config: TConfig) -> TInstance: ...

@runtime_checkable
class Store[TKey, TValue](Protocol):
    async def get(self, key: TKey) -> TValue | None: ...
    async def set(self, key: TKey, value: TValue, ttl: int | None = None) -> None: ...
    async def delete(self, key: TKey) -> bool: ...
```

### 6. Generic Specification Pattern

```python
# src/core/base/specification.py
class Specification[T](ABC):
    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool: ...
    
    def __and__(self, other: Specification[T]) -> AndSpecification[T]: ...
    def __or__(self, other: Specification[T]) -> OrSpecification[T]: ...
    def __invert__(self) -> NotSpecification[T]: ...

class AndSpecification[T](CompositeSpecification[T]): ...
class OrSpecification[T](CompositeSpecification[T]): ...
class NotSpecification[T](CompositeSpecification[T]): ...
class PredicateSpecification[T](Specification[T]): ...
class AttributeSpecification[T](Specification[T]): ...
```

### 7. Generic CRUD Router

```python
# src/interface/router.py
class GenericCRUDRouter[T, CreateDTO, UpdateDTO, ResponseDTO]:
    def __init__(
        self,
        *,
        prefix: str,
        tags: list[str],
        response_model: type[ResponseDTO],
        create_model: type[CreateDTO],
        update_model: type[UpdateDTO],
        use_case_dependency: Callable[..., Any],
    ) -> None: ...
```

### 8. Generic Response DTOs

```python
# src/application/common/dto.py
class ApiResponse[T](BaseModel):
    data: T
    message: str
    status_code: int
    timestamp: datetime
    request_id: str | None

class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int
    
    @computed_field
    def pages(self) -> int: ...
    @computed_field
    def has_next(self) -> bool: ...
    @computed_field
    def has_previous(self) -> bool: ...
```

## Data Models

### Type Definitions (PEP 695)

```python
# src/core/types/repository_types.py
type CRUDRepository[T, CreateT, UpdateT] = IRepository[T, CreateT, UpdateT]
type ReadOnlyRepository[T] = IRepository[T, None, None]
type WriteOnlyRepository[T, CreateT] = IRepository[T, CreateT, None]

type StandardUseCase[T, CreateDTO, UpdateDTO, ResponseDTO] = BaseUseCase[T, CreateDTO, UpdateDTO, ResponseDTO]
type ReadOnlyUseCase[T, ResponseDTO] = BaseUseCase[T, None, None, ResponseDTO]

type ApiResult[T] = ApiResponse[T]
type PaginatedResult[T] = PaginatedResponse[T]
type ErrorResult = ProblemDetail
```

### ID Types

```python
# src/core/types/id_types.py
type ULID = str
type UUID7 = str
type EntityId = str | int
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Repository CRUD Round-Trip
*For any* entity type T and valid create data, creating an entity and then retrieving it by ID should return an equivalent entity.
**Validates: Requirements 1.1, 14.1**

### Property 2: Result Pattern Round-Trip
*For any* Result[T, E] value, serializing to dict and deserializing should produce an equivalent Result.
**Validates: Requirements 4.5**

### Property 3: Specification Composition Associativity
*For any* three specifications A, B, C of type Specification[T], (A & B) & C should be equivalent to A & (B & C).
**Validates: Requirements 12.2**

### Property 4: Specification De Morgan's Laws
*For any* two specifications A, B of type Specification[T], ~(A & B) should be equivalent to (~A | ~B).
**Validates: Requirements 12.2**

### Property 5: Mapper Bidirectional Consistency
*For any* entity E and mapper IMapper[E, DTO], to_dto(to_entity(dto)) should equal dto for valid DTOs.
**Validates: Requirements 2.3**

### Property 6: Pagination Computed Fields
*For any* PaginatedResponse[T] with total > 0 and size > 0, pages should equal ceil(total / size).
**Validates: Requirements 3.4**

### Property 7: Entity Version Increment
*For any* VersionedEntity[IdType, int], calling increment_version should increase version by exactly 1.
**Validates: Requirements 5.3**

### Property 8: Cache Hit/Miss Consistency
*For any* cache operation sequence, hits + misses should equal total get operations.
**Validates: Requirements 7.4**

### Property 9: Result Monadic Laws - Left Identity
*For any* value x and function f: T -> Result[U, E], Ok(x).bind(f) should equal f(x).
**Validates: Requirements 4.1, 4.3**

### Property 10: Result Monadic Laws - Right Identity
*For any* Result[T, E] m, m.bind(Ok) should equal m.
**Validates: Requirements 4.1, 4.3**

### Property 11: Collect Results Aggregation
*For any* list of Ok results, collect_results should return Ok with all values. For any list containing an Err, collect_results should return the first Err.
**Validates: Requirements 4.4**

### Property 12: Use Case Get Type Narrowing
*For any* use case and valid ID, get(id, raise_on_missing=True) should never return None.
**Validates: Requirements 2.2**

### Property 13: Soft Delete Idempotence
*For any* entity, calling delete(id, soft=True) twice should have the same effect as calling it once.
**Validates: Requirements 14.4**

### Property 14: ULID Uniqueness
*For any* two ULIDEntity instances created, their IDs should be unique.
**Validates: Requirements 5.4**

### Property 15: Protocol Runtime Checkable
*For any* class implementing Repository[T, Id] protocol, isinstance check should return True.
**Validates: Requirements 6.5**

## Error Handling

### Error Hierarchy

```python
# src/core/errors/
class DomainError(Exception):
    """Base class for domain errors."""
    
class EntityNotFoundError(DomainError):
    """Entity not found in repository."""
    
class ValidationError(DomainError):
    """Validation failed."""
    
class ApplicationError(Exception):
    """Base class for application errors."""
    
class InfrastructureError(Exception):
    """Base class for infrastructure errors."""
```

### Error Response Format (RFC 7807)

```python
class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    errors: list[dict] | None = None
```

## Testing Strategy

### Dual Testing Approach

1. **Unit Tests**: Verify specific examples and edge cases
2. **Property-Based Tests**: Verify universal properties using Hypothesis

### Property-Based Testing Framework

- **Library**: Hypothesis (already configured in pyproject.toml)
- **Minimum Iterations**: 100 per property
- **Test Location**: `tests/properties/`

### Test Annotation Format

```python
@given(st.builds(Ok, st.integers()))
@settings(max_examples=100)
def test_result_round_trip(result: Ok[int]) -> None:
    """**Feature: python-api-base-2025-generics-audit, Property 2: Result Pattern Round-Trip**
    **Validates: Requirements 4.5**
    """
    serialized = result.to_dict()
    deserialized = result_from_dict(serialized)
    assert deserialized.value == result.value
```

### Existing Test Coverage

The project already has comprehensive property-based tests in `tests/properties/`:
- `test_infrastructure_generics_properties.py`
- `test_interface_layer_generics_properties.py`
- `test_jwt_properties.py`
- `test_rbac_properties.py`
- `test_repository_properties.py`
- `test_caching_properties.py`
- `test_circuit_breaker_properties.py`
- `test_rate_limiter_properties.py`

## Architecture Validation Summary

### Strengths Identified

1. **Excellent Generic Usage**: PEP 695 syntax used throughout
2. **Clean Architecture**: Clear layer separation
3. **Comprehensive Protocols**: Runtime-checkable protocols
4. **Result Pattern**: Full monadic implementation
5. **Specification Pattern**: Composable business rules
6. **Property-Based Testing**: Extensive coverage

### Areas for Potential Enhancement

1. **Generic Resilience Patterns**: Add CircuitBreaker[TConfig], Retry[T]
2. **Generic Multitenancy**: Add TenantContext[TId]
3. **Generic Feature Flags**: Add FeatureFlag[TContext]
4. **Generic GraphQL Support**: Add GraphQLType[T], QueryResolver[T, TArgs]
5. **Generic API Versioning**: Add VersionedRouter[TVersion], ResponseTransformer[TFrom, TTo]
6. **Generic Audit Trail**: Add AuditRecord[T], AuditStore[TProvider]

### Conformance Score: 95/100

The current implementation is already at state-of-the-art level for a Python API Base in 2025. Minor enhancements can be made to add more enterprise features with generic typing.
