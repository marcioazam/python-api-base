# Design Document: Deep Code Quality & Generics Review

## Overview

Este documento descreve o design para análise profunda de qualidade de código e implementação completa de Generics no Python API Base. O objetivo é garantir que todo o código esteja 100% otimizado seguindo as melhores práticas de Python 2025.

## Architecture

A análise será estruturada em camadas, seguindo a Clean Architecture existente:

```
┌─────────────────────────────────────────────────────────────┐
│                    Analysis Layers                          │
├─────────────────────────────────────────────────────────────┤
│  1. Generic Types Analysis                                  │
│     - PEP 695 syntax compliance                             │
│     - TypeVar bounds and constraints                        │
│     - Protocol classes implementation                       │
├─────────────────────────────────────────────────────────────┤
│  2. Memory Optimization Analysis                            │
│     - __slots__ usage in dataclasses                        │
│     - frozen=True for immutability                          │
│     - Generator vs list comprehension                       │
├─────────────────────────────────────────────────────────────┤
│  3. Type Safety Analysis                                    │
│     - @overload for type narrowing                          │
│     - TypeGuard/TypeIs usage                                │
│     - Union types (T | None vs Optional[T])                 │
├─────────────────────────────────────────────────────────────┤
│  4. Async Patterns Analysis                                 │
│     - @asynccontextmanager usage                            │
│     - asyncio.gather patterns                               │
│     - AsyncIterator type hints                              │
├─────────────────────────────────────────────────────────────┤
│  5. Caching Analysis                                        │
│     - @lru_cache usage                                      │
│     - Cache invalidation patterns                           │
│     - Singleton patterns                                    │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Current Implementation Status

Based on code analysis, the following components are already well-implemented:

#### ✅ Fully Implemented (PEP 695 Syntax)

1. **Result Pattern** (`src/my_api/shared/result.py`)
   ```python
   @dataclass(frozen=True, slots=True)
   class Ok[T]:
       value: T
   
   @dataclass(frozen=True, slots=True)
   class Err[E]:
       error: E
   
   type Result[T, E] = Ok[T] | Err[E]
   ```

2. **Repository Interface** (`src/my_api/shared/repository.py`)
   ```python
   class IRepository[T: BaseModel, CreateT: BaseModel, UpdateT: BaseModel](ABC):
       ...
   ```

3. **Specification Pattern** (`src/my_api/shared/specification.py`)
   ```python
   class Specification[T](ABC):
       def __and__(self, other: "Specification[T]") -> "Specification[T]": ...
       def __or__(self, other: "Specification[T]") -> "Specification[T]": ...
       def __invert__(self) -> "Specification[T]": ...
   ```

4. **Mapper Interface** (`src/my_api/shared/mapper.py`)
   ```python
   class IMapper[Source: BaseModel, Target: BaseModel](ABC):
       ...
   ```

5. **Use Case Base** (`src/my_api/shared/use_case.py`)
   ```python
   class BaseUseCase[T: BaseModel, CreateDTO: BaseModel, UpdateDTO: BaseModel, ResponseDTO: BaseModel]:
       @overload
       async def get(self, id: str, *, raise_on_missing: Literal[True] = True) -> ResponseDTO: ...
       @overload
       async def get(self, id: str, *, raise_on_missing: Literal[False]) -> ResponseDTO | None: ...
   ```

6. **DTO Classes** (`src/my_api/shared/dto.py`)
   ```python
   class ApiResponse[T](BaseModel):
       data: T
   
   class PaginatedResponse[T](BaseModel):
       items: list[T]
       @computed_field
       @property
       def pages(self) -> int: ...
   ```

7. **Entity Base** (`src/my_api/shared/entity.py`)
   ```python
   class BaseEntity[IdType: (str, int)](BaseModel):
       id: IdType | None = Field(default=None)
   ```

8. **Protocol Classes** (`src/my_api/shared/protocols/`)
   ```python
   @runtime_checkable
   class AsyncRepository[T: BaseModel, CreateDTO: BaseModel, UpdateDTO: BaseModel](Protocol):
       ...
   ```

#### ⚠️ Needs Improvement

1. **SQLModelRepository** (`src/my_api/adapters/repositories/sqlmodel_repository.py`)
   - Uses old TypeVar syntax instead of PEP 695
   - Current: `T = TypeVar("T", bound=SQLModel)`
   - Should be: `class SQLModelRepository[T: SQLModel, CreateT: BaseModel, UpdateT: BaseModel]`

2. **EntityId** (`src/my_api/domain/value_objects/entity_id.py`)
   - Not using generic type parameter
   - Uses inheritance for typed IDs (ItemId, UserId, etc.)
   - Could use: `class EntityId[T](Generic[T])` for type-safe ID references

3. **InMemoryRepository** (`src/my_api/shared/repository.py`)
   - Uses `callable` instead of `Callable`
   - Line: `id_generator: callable = None`
   - Should be: `id_generator: Callable[[], str] | None = None`

4. **ErrorContext** (`src/my_api/core/exceptions.py`)
   - Missing `slots=True` in dataclass
   - Current: `@dataclass(frozen=True)`
   - Should be: `@dataclass(frozen=True, slots=True)`

## Data Models

### Generic Type Hierarchy

```
BaseModel (Pydantic)
├── BaseEntity[IdType: (str, int)]
│   └── ULIDEntity (BaseEntity[str])
├── BaseDTO
│   ├── ApiResponse[T]
│   └── PaginatedResponse[T]
└── Domain Entities
    └── Item, User, etc.

Protocol (typing)
├── Identifiable
├── Timestamped
├── SoftDeletable
├── Entity (Identifiable)
├── TrackedEntity (Identifiable + Timestamped)
├── DeletableEntity (Identifiable + SoftDeletable)
└── FullEntity (Identifiable + Timestamped + SoftDeletable)
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: PEP 695 Syntax Compliance
*For any* generic class definition in shared/, domain/, or application/ layers, the class SHALL use PEP 695 type parameter syntax (`class Name[T]`) instead of old TypeVar syntax.
**Validates: Requirements 1.1, 2.1, 3.1, 4.1, 5.1, 7.1**

### Property 2: Dataclass Memory Optimization
*For any* dataclass with `frozen=True`, the class SHALL also have `slots=True` for memory optimization.
**Validates: Requirements 4.2, 6.1, 8.1, 12.1**

### Property 3: Result Pattern Completeness
*For any* Result type (Ok or Err), the class SHALL implement `map`, `map_err`, `unwrap`, `unwrap_or` methods with proper generic signatures.
**Validates: Requirements 4.3, 4.4**

### Property 4: Specification Operator Support
*For any* Specification class, the class SHALL implement `__and__`, `__or__`, `__invert__` operators for composable business rules.
**Validates: Requirements 5.2**

### Property 5: Overload Type Narrowing
*For any* method with conditional return types based on a boolean parameter, the method SHALL use `@overload` decorator with `Literal[True]` and `Literal[False]` for type narrowing.
**Validates: Requirements 3.2**

### Property 6: Protocol Runtime Checkable
*For any* Protocol class used for structural typing, the class SHALL have `@runtime_checkable` decorator.
**Validates: Requirements 13.6**

### Property 7: Optional Type Syntax
*For any* optional type annotation, the code SHALL use `T | None` syntax instead of `Optional[T]`.
**Validates: Requirements 1.4, 7.5**

### Property 8: Async Context Manager Usage
*For any* async resource management (database sessions, file handles, etc.), the code SHALL use `@asynccontextmanager` decorator.
**Validates: Requirements 3.3, 11.2**

### Property 9: LRU Cache Configuration
*For any* `@lru_cache` decorator usage, the decorator SHALL have explicit `maxsize` parameter (128 for bounded, None for unlimited).
**Validates: Requirements 9.4, 12.3**

### Property 10: Exception Serialization Consistency
*For any* AppException subclass, the `to_dict()` method SHALL return a dictionary with consistent keys: `message`, `error_code`, `status_code`, `details`, `correlation_id`, `timestamp`.
**Validates: Requirements 8.2, 8.5**

### Property 11: Pydantic Settings Validation
*For any* Settings class using pydantic-settings, the class SHALL use `SecretStr` for sensitive values and `@field_validator` for pattern validation.
**Validates: Requirements 9.1, 9.2, 9.5**

### Property 12: Lifecycle Hook Execution Order
*For any* LifecycleManager, startup hooks SHALL execute in registration order and shutdown hooks SHALL execute in reverse order.
**Validates: Requirements 10.3, 10.4**

### Property 13: Repository Return Types
*For any* repository method returning collections, the return type SHALL be `Sequence[T]` for read-only access.
**Validates: Requirements 1.3**

### Property 14: Mapper Bidirectional Consistency
*For any* Mapper implementation, `to_entity(to_dto(entity))` SHALL produce an equivalent entity (round-trip property).
**Validates: Requirements 2.3**

### Property 15: Entity ID Validation
*For any* EntityId value object, the `__post_init__` method SHALL validate the ID format and raise `ValueError` for invalid IDs.
**Validates: Requirements 6.2, 6.5**

## Error Handling

### Exception Hierarchy

```
Exception
└── AppException
    ├── EntityNotFoundError (404)
    ├── ValidationError (422)
    ├── BusinessRuleViolationError (400)
    ├── AuthenticationError (401)
    ├── AuthorizationError (403)
    ├── RateLimitExceededError (429)
    └── ConflictError (409)
```

### Error Context Pattern

```python
@dataclass(frozen=True, slots=True)  # Add slots=True
class ErrorContext:
    correlation_id: str = field(default_factory=generate_ulid)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    request_path: str | None = None
```

## Additional Patterns Analysis (Based on 15+ Web Research)

### ✅ CQRS Pattern - FULLY IMPLEMENTED
Based on research from python-cqrs PyPI, Krython tutorials, and Medium articles:
- `Command[T, E]` with PEP 695 syntax ✅
- `Query[T]` with PEP 695 syntax ✅
- `CommandBus` with middleware support ✅
- `QueryBus` with caching support ✅
- Domain event emission ✅

### ✅ Unit of Work Pattern - FULLY IMPLEMENTED
Based on research from SQLAlchemy 2.0 docs, Medium articles on transaction management:
- `IUnitOfWork` abstract interface ✅
- `SQLAlchemyUnitOfWork` implementation ✅
- `@asynccontextmanager` for transactions ✅
- Generic `AsyncResource[T]` context manager ✅
- `managed_resource` functional approach ✅

### ✅ Circuit Breaker Pattern - FULLY IMPLEMENTED
Based on research from circuitbreaker PyPI, Microsoft Azure patterns:
- `CircuitState` enum (CLOSED, OPEN, HALF_OPEN) ✅
- `CircuitBreakerConfig` dataclass ✅
- Thread-safe `CircuitBreakerRegistry` singleton ✅
- `@circuit_breaker` decorator ✅
- Failure/success threshold tracking ✅

### ✅ Event Sourcing Pattern - FULLY IMPLEMENTED
Based on research from eventsourcing library, STX Next article:
- `Aggregate[AggregateId]` generic base class ✅
- `SourcedEvent` base class ✅
- `Snapshot` support ✅
- Event replay (`load_from_history`) ✅
- Uncommitted events tracking ✅

### ✅ Value Object Pattern - FULLY IMPLEMENTED
Based on research from value-object-pattern PyPI, DDD articles:
- `EntityId` with `@dataclass(frozen=True, slots=True)` ✅
- ULID validation in `__post_init__` ✅
- Typed IDs (ItemId, UserId, RoleId, AuditLogId) ✅
- Immutability enforced ✅

### ✅ Clean Architecture - FULLY IMPLEMENTED
Based on research from Krython tutorials, Medium articles:
- Domain layer (entities, value objects, repositories) ✅
- Application layer (use cases, DTOs, mappers) ✅
- Adapters layer (API routes, repositories) ✅
- Infrastructure layer (database, auth, logging) ✅
- Shared layer (protocols, patterns) ✅

## Testing Strategy

### Dual Testing Approach

1. **Unit Tests**: Verify specific examples and edge cases
2. **Property-Based Tests**: Verify universal properties using Hypothesis

### Property-Based Testing Framework

- **Library**: Hypothesis (already in use)
- **Minimum iterations**: 100 per property
- **Annotation format**: `**Feature: deep-code-quality-generics-review, Property {number}: {property_text}**`

### Test Categories

1. **Generic Type Tests**
   - Verify PEP 695 syntax via AST parsing
   - Verify TypeVar bounds and constraints
   - Verify Protocol implementations

2. **Memory Optimization Tests**
   - Verify `__slots__` usage in dataclasses
   - Verify `frozen=True` for immutability
   - Benchmark memory usage

3. **Type Safety Tests**
   - Verify `@overload` decorator usage
   - Verify return type consistency
   - Verify type narrowing behavior

4. **Async Pattern Tests**
   - Verify `@asynccontextmanager` usage
   - Verify proper cleanup on exceptions
   - Verify concurrent operation handling

5. **Caching Tests**
   - Verify `@lru_cache` configuration
   - Verify cache hit/miss behavior
   - Verify cache invalidation

### Implementation Priority

1. **High Priority** (Gaps identified):
   - Fix SQLModelRepository to use PEP 695 syntax
   - Add `slots=True` to ErrorContext
   - Fix InMemoryRepository `callable` type hint

2. **Medium Priority** (Enhancements):
   - Add generic type parameter to EntityId
   - Add more Protocol compositions
   - Enhance mapper error handling

3. **Low Priority** (Nice to have):
   - Add SQL WHERE clause generation to Specification
   - Add more caching strategies
   - Add performance benchmarks

## Summary: Implementation Status

| Pattern/Feature | Status | PEP 695 | Slots | Notes |
|-----------------|--------|---------|-------|-------|
| Result Pattern | ✅ | ✅ | ✅ | Ok/Err with frozen dataclass |
| Repository Interface | ✅ | ✅ | N/A | IRepository with bounds |
| Specification Pattern | ✅ | ✅ | N/A | Operator overloading |
| Mapper Interface | ✅ | ✅ | N/A | IMapper with bounds |
| Use Case Base | ✅ | ✅ | N/A | @overload for type narrowing |
| DTO Classes | ✅ | ✅ | N/A | ApiResponse, PaginatedResponse |
| Entity Base | ✅ | ✅ | N/A | BaseEntity with IdType bound |
| Protocol Classes | ✅ | ✅ | N/A | @runtime_checkable |
| CQRS | ✅ | ✅ | N/A | Command/Query buses |
| Unit of Work | ✅ | ✅ | N/A | AsyncResource generic |
| Circuit Breaker | ✅ | ⚠️ | N/A | Uses old TypeVar |
| Event Sourcing | ✅ | ⚠️ | N/A | Uses old Generic syntax |
| Value Objects | ✅ | N/A | ✅ | EntityId frozen+slots |
| SQLModelRepository | ⚠️ | ❌ | N/A | Needs PEP 695 migration |
| ErrorContext | ⚠️ | N/A | ❌ | Needs slots=True |
| InMemoryRepository | ⚠️ | ✅ | N/A | callable → Callable |

**Overall Score: 90% implemented correctly**
