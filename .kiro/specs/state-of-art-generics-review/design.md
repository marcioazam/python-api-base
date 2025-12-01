# Design Document: State-of-Art Generics Review

## Overview

Este documento detalha o design para um code review abrangente focado em Generics (PEP 695), boas práticas, clean code e reutilização de código. O objetivo é transformar a API Python em um estado de arte para 2025, com código conciso, type-safe e altamente reutilizável.

### Análise do Estado Atual

**Pontos Fortes Identificados:**
- Uso consistente de PEP 695 type parameter syntax em módulos core
- Result pattern bem implementado com operações monádicas
- Protocols com `@runtime_checkable` para duck typing
- DTOs genéricos com computed properties (PaginatedResponse, BatchResponse)
- Repository pattern com suporte a cursor pagination

**Oportunidades de Melhoria:**
1. Inconsistência de nomenclatura de type parameters entre módulos
2. Duplicação de patterns similares (ex: múltiplos EventHandler protocols)
3. Alguns módulos ainda usam TypeVar ao invés de PEP 695
4. Falta de consolidação de mensagens de erro e status codes
5. Handlers usando Generic[T, U] ao invés de PEP 695 syntax

## Architecture

```mermaid
graph TB
    subgraph "Application Layer"
        UC[Use Cases<br/>BaseUseCase[TEntity, TId]]
        CMD[Commands<br/>Command[T, E]]
        QRY[Queries<br/>Query[T]]
        DTO[DTOs<br/>ApiResponse[T], PaginatedResponse[T]]
    end
    
    subgraph "Core Layer"
        ENT[Entities<br/>BaseEntity[IdType]]
        REPO[Repository<br/>IRepository[T, CreateT, UpdateT, IdType]]
        RES[Result<br/>Result[T, E] = Ok[T] | Err[E]]
        PAT[Patterns<br/>Validator[T], Mapper[S, T]]
    end
    
    subgraph "Infrastructure Layer"
        CACHE[Cache<br/>CacheProvider[T], CacheKey[T]]
        MSG[Messaging<br/>EventBus[TEvent], MessageHandler[T, R]]
        HTTP[HTTP<br/>HttpClient[TReq, TRes], RetryPolicy[TEx]]
        SEC[Security<br/>Authorizer[TRes, TAct], RateLimiter[TKey]]
        OBS[Observability<br/>Counter[TLabels], HealthCheck[TDep]]
    end
    
    UC --> REPO
    UC --> RES
    CMD --> RES
    QRY --> DTO
    REPO --> ENT
    MSG --> RES
```

## Components and Interfaces

### 1. Core Generics Consolidation

```python
# Nomenclatura padronizada de Type Parameters
T = Entity type genérico
E = Error type
TInput, TOutput = Transformações
TKey, TValue = Mappings
TEntity, TCommand, TQuery, TEvent = Domain-specific
IdType = ID type (str | int)
```

### 2. Result Pattern Enhancement

```python
# src/core/base/result.py - Já bem implementado
type Result[T, E] = Ok[T] | Err[E]

# Operações monádicas disponíveis:
# - map, bind, and_then, or_else
# - match, flatten, inspect
# - try_catch, try_catch_async, collect_results
```

### 3. Repository Interface Consolidation

```python
# Interface unificada com 4 type parameters
class IRepository[T: BaseModel, CreateT: BaseModel, UpdateT: BaseModel, IdType: (str, int) = str]:
    async def get_by_id(self, id: IdType) -> T | None
    async def get_all(...) -> tuple[Sequence[T], int]
    async def create(self, data: CreateT) -> T
    async def update(self, id: IdType, data: UpdateT) -> T | None
    async def delete(self, id: IdType, *, soft: bool = True) -> bool
    async def create_many(self, data: Sequence[CreateT]) -> Sequence[T]
    async def exists(self, id: IdType) -> bool
    async def get_page(...) -> CursorPage[T, str]
```

### 4. Event/Message Handler Consolidation

```python
# Consolidar múltiplos EventHandler protocols em um único
@runtime_checkable
class EventHandler[TEvent](Protocol):
    async def handle(self, event: TEvent) -> None: ...

# MessageHandler com resultado tipado
@runtime_checkable
class MessageHandler[TMessage, TResult](Protocol):
    async def handle(self, message: TMessage) -> TResult: ...
```

### 5. Validation Framework

```python
# Framework unificado de validação
@dataclass(frozen=True, slots=True)
class ValidationResult[T]:
    value: T | None = None
    errors: list[ValidationError] = field(default_factory=list)
    
    def to_result(self) -> Result[T, list[ValidationError]]: ...

@runtime_checkable
class Validator[T](Protocol):
    def validate(self, value: T) -> ValidationResult[T]: ...
```

## Data Models

### Generic DTOs

```python
# ApiResponse[T] - Wrapper padrão
class ApiResponse[T](BaseModel):
    data: T
    message: str = "Success"
    status_code: int = 200
    timestamp: datetime
    request_id: str | None

# PaginatedResponse[T] - Paginação offset
class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int
    # computed: pages, has_next, has_previous

# CursorPaginatedResponse[T, TCursor] - Paginação cursor
class CursorPaginatedResponse[T, TCursor](BaseModel):
    items: list[T]
    next_cursor: TCursor | None
    prev_cursor: TCursor | None
    has_more: bool

# BatchResponse[T, TError] - Operações em lote
class BatchResponse[T, TError](BaseModel):
    succeeded: list[T]
    failed: list[TError]
    total_count: int
    success_count: int
    failure_count: int
    # computed: success_rate
```

### Entity Hierarchy

```python
# BaseEntity[IdType] - Base com timestamps
# AuditableEntity[IdType] - + created_by, updated_by
# VersionedEntity[IdType, VersionT] - + version para optimistic locking
# AuditableVersionedEntity[IdType, VersionT] - Combinação completa
# ULIDEntity, AuditableULIDEntity, VersionedULIDEntity - Especializações com ULID
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Result Pattern Round-Trip
*For any* value T and error E, wrapping in Ok/Err and unwrapping should preserve the original value.
**Validates: Requirements 3.1, 3.2**

### Property 2: Result Monadic Laws
*For any* Result[T, E], the monadic operations (map, bind) should satisfy identity and associativity laws.
**Validates: Requirements 3.2**

### Property 3: PaginatedResponse Computed Properties
*For any* PaginatedResponse with total > 0 and size > 0, pages should equal ceil(total/size), has_next should be page < pages, has_previous should be page > 1.
**Validates: Requirements 5.1**

### Property 4: BatchResult Success Rate
*For any* BatchResult, success_rate should equal (total_succeeded / total_processed) * 100, or 0 if total_processed is 0.
**Validates: Requirements 5.3, 22.3**

### Property 5: Repository CRUD Consistency
*For any* entity created via repository.create(), calling repository.get_by_id() with the same ID should return an equivalent entity.
**Validates: Requirements 6.1, 6.2**

### Property 6: Repository Soft Delete
*For any* entity, calling delete(id, soft=True) should mark is_deleted=True, and subsequent get_by_id should return None.
**Validates: Requirements 6.4**

### Property 7: Cache Round-Trip
*For any* value T, cache.set(key, value) followed by cache.get(key) should return the same value.
**Validates: Requirements 9.2, 9.3**

### Property 8: Cache Tag Invalidation
*For any* set of entries with tag T, invalidate_by_tag(T) should remove all entries with that tag.
**Validates: Requirements 9.4**

### Property 9: EventBus Delivery
*For any* event published to EventBus, all subscribed handlers for that event type should receive the event.
**Validates: Requirements 8.1, 8.2**

### Property 10: EventBus Error Isolation
*For any* event with multiple handlers, if one handler fails, other handlers should still receive and process the event.
**Validates: Requirements 8.3**

### Property 11: Rate Limiter Enforcement
*For any* RateLimiter with max_requests=N, the (N+1)th request within the window should be denied.
**Validates: Requirements 13.3**

### Property 12: Retry Policy Backoff
*For any* ExponentialBackoff policy, get_delay(attempt) should equal min(base_delay * (exponential_base ** attempt), max_delay).
**Validates: Requirements 10.3**

### Property 13: TenantContext Isolation
*For any* TenantContext(tenant_id), all repository operations within the context should be filtered by that tenant_id.
**Validates: Requirements 20.1, 20.2**

### Property 14: Validation Result Consistency
*For any* ValidationResult, is_valid should be True iff errors is empty and value is not None.
**Validates: Requirements 2.4**

### Property 15: Feature Flag Percentage Consistency
*For any* flag with percentage P and user U, repeated evaluations should always return the same result (consistent hashing).
**Validates: Requirements 18.1, 18.2**

### Property 16: File Validation Checksum
*For any* valid file, validate_file should return Ok with SHA-256 checksum of the content.
**Validates: Requirements 19.2**

### Property 17: Batch Operation Chunking
*For any* batch operation with chunk_size=N, items should be processed in chunks of at most N items.
**Validates: Requirements 22.1, 22.2**

### Property 18: Read DTO Immutability
*For any* read DTO with frozen=True, attempting to modify attributes should raise FrozenInstanceError.
**Validates: Requirements 24.1**

## Error Handling

### Standardized Error Types

```python
# Use Case Errors
class UseCaseError(Exception):
    message: str
    code: str | None

class NotFoundError(UseCaseError):
    entity_type: str
    entity_id: Any

class ValidationError(UseCaseError):
    errors: list[dict[str, Any]]

# Upload Errors (Enum)
class UploadError(Enum):
    FILE_TOO_LARGE = "file_too_large"
    INVALID_TYPE = "invalid_type"
    INVALID_EXTENSION = "invalid_extension"
    QUOTA_EXCEEDED = "quota_exceeded"
    VIRUS_DETECTED = "virus_detected"
    STORAGE_ERROR = "storage_error"
    CHECKSUM_MISMATCH = "checksum_mismatch"

# Handler Errors
class HandlerNotFoundError(Exception):
    handler_type: type
```

### Error Response Pattern

```python
# Usar Result[T, E] para operações que podem falhar
async def create(self, data: CreateT) -> Result[TEntity, UseCaseError]:
    validation = await self._validate_create(data)
    if validation.is_err():
        return validation
    # ...
    return Ok(entity)
```

## Testing Strategy

### Dual Testing Approach

**Unit Tests:**
- Testes específicos para edge cases
- Validação de comportamentos específicos
- Integração entre componentes

**Property-Based Tests (Hypothesis):**
- Validação de propriedades universais
- Testes de round-trip para serialização
- Verificação de invariantes

### Property-Based Testing Framework

```python
# Usar Hypothesis para Python
from hypothesis import given, strategies as st

@given(st.text(), st.integers())
def test_result_round_trip(value, error):
    """**Feature: state-of-art-generics-review, Property 1: Result Pattern Round-Trip**
    **Validates: Requirements 3.1, 3.2**
    """
    ok_result = Ok(value)
    assert ok_result.unwrap() == value
    
    err_result = Err(error)
    assert err_result.error == error
```

### Test Configuration

- Minimum 100 iterations per property test
- Use smart generators for domain-specific types
- Tag each test with property reference
