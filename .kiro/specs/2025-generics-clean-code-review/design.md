# Design Document: 2025 Generics & Clean Code Review

## Overview

Este documento descreve o design para uma revisão abrangente de código focada em Generics (PEP 695), Clean Code, reutilização e padronização. O objetivo é transformar a API Python em um estado-da-arte para 2025, com código conciso, type-safe e altamente reutilizável.

### Escopo da Revisão

**Arquivos Analisados:**
- `src/domain/common/` - Value Objects, Specifications, Mixins
- `src/domain/users/` - Aggregates, Entities, Events, Repositories
- `src/shared/` - Validation, Utils, Localization, Caching
- `src/core/base/` - Entity, Repository, Result
- `src/core/patterns/` - Generics patterns
- `src/application/common/` - DTOs, Handlers, Bus

### Problemas Identificados

1. **Inconsistência PEP 695**: Alguns arquivos usam sintaxe moderna, outros ainda usam `Generic[T]`
2. **Type Bounds Ausentes**: Alguns generics não têm bounds apropriados
3. **Duplicação de Value Objects**: `Money` definido em múltiplos lugares
4. **Falta de Padronização**: Diferentes estilos de factory methods
5. **Mensagens Hardcoded**: Strings de erro não centralizadas

## Architecture

```mermaid
graph TB
    subgraph "Domain Layer"
        VO[Value Objects<br/>@dataclass frozen slots]
        SPEC[Specifications<br/>BaseSpecification[T]]
        AGG[Aggregates<br/>AggregateRoot[IdType]]
        ENT[Entities<br/>BaseEntity[IdType]]
        EVT[Domain Events<br/>DomainEvent]
    end
    
    subgraph "Application Layer"
        CMD[Commands<br/>BaseCommand]
        QRY[Queries<br/>BaseQuery]
        HDL[Handlers<br/>CommandHandler[C,R]<br/>QueryHandler[Q,R]]
        DTO[DTOs<br/>ApiResponse[T]<br/>PaginatedResponse[T]]
    end
    
    subgraph "Core Layer"
        RES[Result[T,E]<br/>Ok[T] | Err[E]]
        REPO[IRepository[T,IdType]]
        PAT[Patterns<br/>Validator[T]<br/>Factory[T]]
    end
    
    subgraph "Shared Layer"
        VAL[Validators]
        UTIL[Utils]
        I18N[i18n]
        CACHE[Caching]
    end
    
    HDL --> CMD
    HDL --> QRY
    HDL --> RES
    AGG --> ENT
    AGG --> EVT
    AGG --> VO
    REPO --> ENT
    REPO --> SPEC
```

## Components and Interfaces

### 1. Generic Base Classes (PEP 695)

```python
# Padrão para classes genéricas
class BaseEntity[IdType: (str, int)](BaseModel):
    """Entity base com ID genérico."""
    id: IdType | None = None
    created_at: datetime
    updated_at: datetime

class IRepository[T: BaseEntity, IdType: (str, int)](ABC):
    """Interface de repositório genérico."""
    async def get(self, id: IdType) -> T | None: ...
    async def list(self, spec: Specification[T] | None = None) -> list[T]: ...
    async def create(self, entity: T) -> T: ...
    async def update(self, entity: T) -> T: ...
    async def delete(self, id: IdType) -> bool: ...
```

### 2. Value Object Pattern

```python
# Padrão para Value Objects
@dataclass(frozen=True, slots=True)
class Email(BaseValueObject):
    """Email value object."""
    value: str
    
    def __post_init__(self) -> None:
        if not self._is_valid(self.value):
            raise ValueError(f"Invalid email: {self.value}")
    
    @classmethod
    def create(cls, value: str) -> Self:
        return cls(value=value.lower().strip())
    
    def __str__(self) -> str:
        return self.value
```

### 3. Result Pattern

```python
# Padrão para Result
type Result[T, E] = Ok[T] | Err[E]

@dataclass(frozen=True, slots=True)
class Ok[T]:
    value: T
    def map[U](self, fn: Callable[[T], U]) -> Ok[U]: ...
    def bind[U, F](self, fn: Callable[[T], Result[U, F]]) -> Result[U, F]: ...
    def to_dict(self) -> dict[str, Any]: ...

@dataclass(frozen=True, slots=True)
class Err[E]:
    error: E
    def map_err[F](self, fn: Callable[[E], F]) -> Err[F]: ...
    def to_dict(self) -> dict[str, Any]: ...
```

### 4. Specification Pattern

```python
# Padrão para Specifications
class BaseSpecification[T](ABC):
    """Specification base com suporte SQL."""
    
    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool: ...
    
    @abstractmethod
    def to_sql_condition(self, model_class: type) -> Any: ...
    
    def __and__(self, other: BaseSpecification[T]) -> BaseSpecification[T]: ...
    def __or__(self, other: BaseSpecification[T]) -> BaseSpecification[T]: ...
    def __invert__(self) -> BaseSpecification[T]: ...
```

### 5. Handler Pattern (CQRS)

```python
# Padrão para Handlers
class CommandHandler[TCommand: BaseCommand, TResult](ABC):
    @abstractmethod
    async def handle(self, command: TCommand) -> Result[TResult, Exception]: ...

class QueryHandler[TQuery: BaseQuery, TResult](ABC):
    @abstractmethod
    async def handle(self, query: TQuery) -> Result[TResult, Exception]: ...
```

### 6. DTO Pattern

```python
# Padrão para DTOs
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
```

## Data Models

### Consolidação de Value Objects

| Value Object | Localização Atual | Ação |
|-------------|-------------------|------|
| Money | `domain/common/value_objects.py`, `domain/common/currency.py` | Consolidar em `domain/common/value_objects.py` |
| Email | `domain/users/value_objects.py`, `domain/common/value_objects_common.py` | Consolidar em `shared/value_objects/` |
| PhoneNumber | `domain/users/value_objects.py`, `domain/common/value_objects_common.py` | Consolidar em `shared/value_objects/` |

### Hierarquia de Entidades

```
BaseEntity[IdType]
├── AuditableEntity[IdType]
│   └── AuditableULIDEntity
├── VersionedEntity[IdType, VersionT]
│   └── VersionedULIDEntity
├── AuditableVersionedEntity[IdType, VersionT]
└── ULIDEntity
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: PEP 695 Syntax Consistency

*For any* generic class or function in the codebase, the type parameter declaration SHALL use PEP 695 syntax (`class Name[T]:` or `def func[T]():`) instead of legacy `Generic[T]` or `TypeVar` patterns.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

### Property 2: Type Bounds Consistency

*For any* generic type parameter that operates on domain entities, the type parameter SHALL have an appropriate bound (e.g., `T: BaseEntity`, `TCommand: BaseCommand`) to ensure type safety.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

### Property 3: Generic Pattern Reuse

*For any* repository implementation, the class SHALL extend `IRepository[T, IdType]` with properly bounded type parameters, ensuring consistent CRUD interface across all repositories.

**Validates: Requirements 3.2, 3.3, 3.4, 3.5**

### Property 4: Value Object Pattern Consistency

*For any* value object class, the class SHALL be decorated with `@dataclass(frozen=True, slots=True)`, implement validation in `__post_init__`, provide a `create` classmethod, and implement `__str__`.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

### Property 5: Result Pattern Round-Trip

*For any* `Result[T, E]` value (either `Ok[T]` or `Err[E]`), serializing via `to_dict()` and deserializing via `result_from_dict()` SHALL produce an equivalent Result with the same type discriminator and value/error.

**Validates: Requirements 5.5, 13.1**

### Property 6: Specification Composition

*For any* two specifications `spec1` and `spec2` of type `Specification[T]`, the composed specifications `spec1 & spec2`, `spec1 | spec2`, and `~spec1` SHALL correctly evaluate `is_satisfied_by` according to boolean logic.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

### Property 7: Repository Interface Compliance

*For any* repository implementing `IRepository[T, IdType]`, the repository SHALL provide all required methods (`get`, `list`, `create`, `update`, `delete`) with correct type signatures.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

### Property 8: Handler Type Safety

*For any* command handler extending `CommandHandler[TCommand, TResult]`, the `handle` method SHALL accept exactly `TCommand` and return `Result[TResult, Exception]`.

**Validates: Requirements 8.1, 8.2, 8.3, 8.4**

### Property 9: DTO Response Consistency

*For any* API endpoint returning data, single items SHALL be wrapped in `ApiResponse[T]` and lists SHALL be wrapped in `PaginatedResponse[T]` with correct computed fields.

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

### Property 10: Enum Status Codes

*For any* status code or state value used in the system, the value SHALL be defined as an Enum member rather than a magic string or number.

**Validates: Requirements 10.2, 10.4, 10.5**

### Property 11: Code Metrics Compliance

*For any* function in the codebase, the function SHALL have at most 50 lines. *For any* class, the class SHALL have at most 300 lines. *For any* code block, nesting SHALL not exceed 3 levels.

**Validates: Requirements 11.1, 11.2, 11.3**

### Property 12: Documentation Consistency

*For any* public function or class, the entity SHALL have a docstring. *For any* generic class, the docstring SHALL document type parameters. *For any* optional parameter, the type hint SHALL use `X | None` syntax.

**Validates: Requirements 12.1, 12.2, 12.3, 12.5**

### Property 13: Entity Serialization Round-Trip

*For any* entity extending `BaseEntity[IdType]`, serializing via `model_dump()` and deserializing via `model_validate()` SHALL preserve `id`, `created_at`, and `updated_at` fields.

**Validates: Requirements 13.2, 13.3**

### Property 14: Pagination Cursor Preservation

*For any* cursor-based pagination result, the `next_cursor` value SHALL be decodable and usable to retrieve the next page of results.

**Validates: Requirements 13.4, 13.5**

## Error Handling

### Estratégia de Erros

| Tipo de Erro | Tratamento | Exemplo |
|-------------|------------|---------|
| Validation | `Result[T, ValidationError]` | Campo inválido |
| NotFound | `Result[T, NotFoundError]` | Entidade não existe |
| Business Rule | `Result[T, DomainError]` | Regra violada |
| Infrastructure | `Result[T, InfraError]` | DB/Network falha |

### Constantes de Mensagens

```python
# src/core/errors/constants.py
class ErrorMessages(str, Enum):
    NOT_FOUND = "Resource {resource_type} with ID {id} not found"
    VALIDATION_FAILED = "Validation failed for field {field}: {reason}"
    UNAUTHORIZED = "Authentication required"
    FORBIDDEN = "Permission denied for action {action}"
```

## Testing Strategy

### Dual Testing Approach

1. **Unit Tests**: Verificam exemplos específicos e edge cases
2. **Property-Based Tests**: Verificam propriedades universais

### Property-Based Testing Framework

- **Library**: `hypothesis` (Python)
- **Minimum Iterations**: 100 per property
- **Annotation Format**: `**Feature: 2025-generics-clean-code-review, Property {N}: {name}**`

### Test Structure

```python
from hypothesis import given, strategies as st

class TestResultRoundTrip:
    """Property tests for Result pattern.
    
    **Feature: 2025-generics-clean-code-review, Property 5: Result Pattern Round-Trip**
    **Validates: Requirements 5.5, 13.1**
    """
    
    @given(st.integers())
    def test_ok_round_trip(self, value: int) -> None:
        """Ok values survive round-trip serialization."""
        original = Ok(value)
        serialized = original.to_dict()
        deserialized = result_from_dict(serialized)
        assert deserialized.is_ok()
        assert deserialized.unwrap() == value
    
    @given(st.text())
    def test_err_round_trip(self, error: str) -> None:
        """Err values survive round-trip serialization."""
        original = Err(error)
        serialized = original.to_dict()
        deserialized = result_from_dict(serialized)
        assert deserialized.is_err()
        assert deserialized.error == error
```

### Unit Test Examples

```python
class TestValueObjectPattern:
    """Unit tests for value object consistency."""
    
    def test_email_validation(self) -> None:
        """Email rejects invalid format."""
        with pytest.raises(ValueError):
            Email("invalid")
    
    def test_email_normalization(self) -> None:
        """Email normalizes to lowercase."""
        email = Email.create("Test@Example.COM")
        assert str(email) == "test@example.com"
```

## Refactoring Plan

### Phase 1: Consolidação de Value Objects
- Unificar `Money` em único local
- Unificar `Email`, `PhoneNumber` em `shared/value_objects/`
- Garantir padrão `@dataclass(frozen=True, slots=True)`

### Phase 2: Atualização PEP 695
- Converter `Generic[T]` para `class Name[T]:`
- Converter `TypeVar` para type parameters
- Converter `Optional[X]` para `X | None`

### Phase 3: Type Bounds
- Adicionar bounds em repositórios
- Adicionar bounds em handlers
- Adicionar bounds em specifications

### Phase 4: Padronização de Mensagens
- Centralizar mensagens de erro
- Usar Enums para status codes
- Implementar i18n keys

### Phase 5: Code Metrics
- Refatorar funções > 50 linhas
- Refatorar classes > 300 linhas
- Reduzir nesting > 3 níveis

