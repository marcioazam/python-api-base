# Design Document: Python API Architecture 2025

## Overview

Este documento descreve o design arquitetural para uma API Python moderna e enterprise-ready, focando em:

1. **Uso extensivo de Generics (PEP 695)** para máxima reutilização de código
2. **Clean Architecture / Hexagonal Architecture** para separação de concerns
3. **Patterns modernos** (Repository, Unit of Work, CQRS, Result, Specification)
4. **Features enterprise** (Resilience, Caching, Multitenancy, Observability)
5. **Zero duplicação de código** através de abstrações genéricas

### Princípios de Design

- **DRY (Don't Repeat Yourself)**: Toda lógica reutilizável deve ser abstraída em componentes genéricos
- **SOLID**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **Type Safety**: Uso de Generics PEP 695 para garantir type safety em tempo de compilação
- **Composition over Inheritance**: Preferir composição e protocolos sobre herança profunda

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Interface Layer                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │  REST API   │ │   GraphQL   │ │    gRPC     │ │  Webhooks │ │
│  │ (FastAPI)   │ │ (Strawberry)│ │             │ │           │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Generic Endpoints Factory                      ││
│  │         GenericEndpoints[T, CreateT, UpdateT, ResponseT]    ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              BaseUseCase[T, CreateDTO, UpdateDTO, ResponseDTO]│
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │CommandHandler│ │QueryHandler │ │   Mapper    │ │    DTO    │ │
│  │  [T, R]     │ │   [T, R]    │ │ [Src, Tgt]  │ │ Generics  │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Domain Layer                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ BaseEntity  │ │AggregateRoot│ │ ValueObject │ │  Domain   │ │
│  │  [IdType]   │ │  [IdType]   │ │             │ │  Events   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Specification[T] Pattern                       ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │         IRepository[T, CreateT, UpdateT] Protocol           ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │SQLModelRepo │ │InMemoryRepo │ │  UnitOfWork │ │   Cache   │ │
│  │[T,C,U]      │ │  [T,C,U]    │ │             │ │ Provider  │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Generic Repository Interface

```python
class IRepository[T: BaseModel, CreateT: BaseModel, UpdateT: BaseModel](ABC):
    """Generic repository interface using PEP 695 syntax."""
    
    @abstractmethod
    async def get_by_id(self, id: str) -> T | None: ...
    
    @abstractmethod
    async def get_all(
        self, *, skip: int = 0, limit: int = 100,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None, sort_order: str = "asc"
    ) -> tuple[Sequence[T], int]: ...
    
    @abstractmethod
    async def create(self, data: CreateT) -> T: ...
    
    @abstractmethod
    async def update(self, id: str, data: UpdateT) -> T | None: ...
    
    @abstractmethod
    async def delete(self, id: str, *, soft: bool = True) -> bool: ...
    
    @abstractmethod
    async def exists(self, id: str) -> bool: ...
    
    @abstractmethod
    async def create_many(self, data: Sequence[CreateT]) -> Sequence[T]: ...
```

### 2. Generic Use Case

```python
class BaseUseCase[T: BaseModel, CreateDTO: BaseModel, UpdateDTO: BaseModel, ResponseDTO: BaseModel]:
    """Generic use case with CRUD operations."""
    
    def __init__(
        self,
        repository: IRepository[T, CreateDTO, UpdateDTO],
        mapper: IMapper[T, ResponseDTO],
        entity_name: str = "Entity",
        unit_of_work: IUnitOfWork | None = None,
    ) -> None: ...
    
    @overload
    async def get(self, id: str, *, raise_on_missing: Literal[True] = True) -> ResponseDTO: ...
    
    @overload
    async def get(self, id: str, *, raise_on_missing: Literal[False]) -> ResponseDTO | None: ...
    
    async def list(self, *, page: int = 1, size: int = 20, ...) -> PaginatedResponse[ResponseDTO]: ...
    
    async def create(self, data: CreateDTO) -> ResponseDTO: ...
    
    async def update(self, id: str, data: UpdateDTO) -> ResponseDTO: ...
    
    async def delete(self, id: str) -> bool: ...
```

### 3. Generic Mapper

```python
class IMapper[Source: BaseModel, Target: BaseModel](ABC):
    """Generic mapper interface."""
    
    @abstractmethod
    def to_dto(self, entity: Source) -> Target: ...
    
    @abstractmethod
    def to_entity(self, dto: Target) -> Source: ...
    
    def to_dto_list(self, entities: Sequence[Source]) -> list[Target]: ...
    
    def to_entity_list(self, dtos: Sequence[Target]) -> list[Source]: ...


class AutoMapper[Source: BaseModel, Target: BaseModel](IMapper[Source, Target]):
    """Auto mapper that infers mapping from field names."""
    pass
```

### 4. Result Pattern

```python
@dataclass(frozen=True, slots=True)
class Ok[T]:
    value: T
    def is_ok(self) -> bool: return True
    def unwrap(self) -> T: return self.value
    def map[U](self, fn: Callable[[T], U]) -> Ok[U]: return Ok(fn(self.value))

@dataclass(frozen=True, slots=True)
class Err[E]:
    error: E
    def is_err(self) -> bool: return True
    def unwrap(self) -> Never: raise ValueError(f"Called unwrap on Err: {self.error}")
    def map_err[U](self, fn: Callable[[E], U]) -> Err[U]: return Err(fn(self.error))

type Result[T, E] = Ok[T] | Err[E]
```

### 5. Generic Protocols

```python
@runtime_checkable
class AsyncRepository[T: BaseModel, CreateDTO: BaseModel, UpdateDTO: BaseModel](Protocol):
    async def get_by_id(self, entity_id: Any) -> T | None: ...
    async def create(self, data: CreateDTO) -> T: ...
    async def update(self, entity_id: Any, data: UpdateDTO) -> T | None: ...
    async def delete(self, entity_id: Any) -> bool: ...

@runtime_checkable
class CacheProvider(Protocol):
    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...

@runtime_checkable
class EventHandler[T](Protocol):
    async def handle(self, event: T) -> None: ...

@runtime_checkable
class UnitOfWork(Protocol):
    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
```

### 6. Generic Endpoints Factory

```python
class GenericEndpoints[T: SQLModel, CreateSchemaType: BaseModel, UpdateSchemaType: BaseModel, ResponseSchemaType: BaseModel]:
    """Generic CRUD endpoints generator."""
    
    def __init__(
        self,
        service: GenericService[T, CreateSchemaType, UpdateSchemaType, ResponseSchemaType],
        create_schema: type[CreateSchemaType],
        update_schema: type[UpdateSchemaType],
        response_schema: type[ResponseSchemaType],
        prefix: str = "",
        tags: list[str] | None = None,
        config: EndpointConfig | None = None,
    ) -> None: ...
    
    @property
    def router(self) -> APIRouter: ...
```

### 7. Generic DTOs

```python
class ApiResponse[T](BaseModel):
    data: T
    message: str = "Success"
    status_code: int = 200
    timestamp: datetime
    request_id: str | None = None

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

### Base Entity

```python
class BaseEntity[IdType: (str, int)](BaseModel):
    id: IdType | None = None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False

class ULIDEntity(BaseEntity[str]):
    id: str | None = Field(default_factory=generate_ulid)
```

### Annotated Types

```python
# ID Types
ULID = Annotated[str, StringConstraints(min_length=26, max_length=26, pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$")]
UUID = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{8}-...")]

# String Types
NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
Email = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9._%+-]+@...")]

# Numeric Types
PositiveInt = Annotated[int, Field(gt=0)]
Percentage = Annotated[float, Field(ge=0, le=100)]

# Type Aliases (PEP 695)
type FilterDict = dict[str, Any]
type SortOrder = Literal['asc', 'desc']
type Result[T, E] = Ok[T] | Err[E]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Repository CRUD Round-Trip
*For any* entity created via repository.create(), calling repository.get_by_id() with the returned ID should return an equivalent entity.
**Validates: Requirements 1.2, 1.3, 1.4**

### Property 2: Mapper Bidirectional Consistency
*For any* entity, mapping to DTO and back to entity should preserve all mapped fields: `to_entity(to_dto(entity)).field == entity.field` for all mapped fields.
**Validates: Requirements 3.3, 3.4**

### Property 3: Result Pattern Monad Laws
*For any* Result value, the map operation should satisfy identity law: `result.map(lambda x: x) == result` and composition should be associative.
**Validates: Requirements 4.2, 4.3, 4.5**

### Property 4: Pagination Computation Correctness
*For any* PaginatedResponse with total > 0 and size > 0, pages should equal `ceil(total / size)`, has_next should be `page < pages`, and has_previous should be `page > 1`.
**Validates: Requirements 8.2, 8.3**

### Property 5: Annotated Type Validation
*For any* string matching ULID pattern, validation should pass; for any string not matching, validation should fail with appropriate error.
**Validates: Requirements 10.1, 10.2, 10.3**

### Property 6: Specification Boolean Algebra
*For any* specifications A and B, `(A AND B).is_satisfied_by(x)` should equal `A.is_satisfied_by(x) and B.is_satisfied_by(x)`, and similarly for OR and NOT.
**Validates: Requirements 11.3, 11.4**

### Property 7: Use Case Transaction Atomicity
*For any* sequence of operations within a transaction context, either all operations succeed and are committed, or all are rolled back on failure.
**Validates: Requirements 2.4**

### Property 8: Cache Decorator Idempotence
*For any* cached function call with same arguments, subsequent calls within TTL should return identical results without re-executing the function.
**Validates: Requirements 13.1, 13.2, 13.3**

### Property 9: Rate Limiter Enforcement
*For any* rate limiter configured with limit L and window W, no more than L requests should be allowed within any window of duration W.
**Validates: Requirements 14.2**

### Property 10: Tenant Isolation
*For any* query executed in a tenant context, results should only include records belonging to that tenant.
**Validates: Requirements 19.3, 19.4**

### Property 11: Health Check Aggregation
*For any* set of health checks where at least one fails, the aggregate health status should be unhealthy.
**Validates: Requirements 21.2, 21.5**

### Property 12: API Versioning Routing
*For any* request with version header or path, the system should route to the correct version handler.
**Validates: Requirements 23.1, 23.2, 23.3**

## Error Handling

### Exception Hierarchy

```python
class AppException(Exception):
    """Base application exception with tracing support."""
    message: str
    error_code: str
    status_code: int
    details: dict[str, Any]
    context: ErrorContext

class EntityNotFoundError(AppException): ...  # 404
class ValidationError(AppException): ...       # 422
class AuthenticationError(AppException): ...   # 401
class AuthorizationError(AppException): ...    # 403
class ConflictError(AppException): ...         # 409
class RateLimitExceededError(AppException): ... # 429
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
2. **Property-Based Tests**: Verify universal properties across all inputs

### Property-Based Testing Framework

- **Library**: Hypothesis (Python)
- **Minimum iterations**: 100 per property
- **Annotation format**: `**Feature: python-api-architecture-2025, Property {N}: {description}**`

### Test Categories

| Category | Description | Example |
|----------|-------------|---------|
| Round-trip | Operation + inverse = identity | Mapper to_dto/to_entity |
| Invariant | Property preserved after operation | Collection size after filter |
| Idempotence | f(x) = f(f(x)) | Cache decorator |
| Metamorphic | Known relationship between inputs/outputs | Pagination computation |
| Model-based | Compare optimized vs reference implementation | Query builder |

### Test Structure

```python
from hypothesis import given, strategies as st

class TestRepositoryProperties:
    """Property-based tests for repository pattern."""
    
    @given(st.builds(CreateDTO, name=st.text(min_size=1)))
    def test_create_get_round_trip(self, create_dto: CreateDTO):
        """
        **Feature: python-api-architecture-2025, Property 1: Repository CRUD Round-Trip**
        **Validates: Requirements 1.2, 1.3, 1.4**
        """
        entity = await repository.create(create_dto)
        retrieved = await repository.get_by_id(entity.id)
        assert retrieved is not None
        assert retrieved.name == create_dto.name
```
