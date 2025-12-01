# Requirements Document

## Introduction

Este documento define os requisitos para validação e melhoria da arquitetura da API Python em `/src`, focando em boas práticas modernas de 2025, uso extensivo de Generics (PEP 695), eliminação de código duplicado, e implementação de todos os módulos e features essenciais que uma API Python enterprise deve ter.

A análise é baseada em pesquisas extensivas de APIs Python modernas, incluindo FastAPI best practices, Clean Architecture, Hexagonal Architecture, CQRS, Event Sourcing, e patterns de resiliência.

## Glossary

- **Generic**: Tipo parametrizado que permite reutilização de código com type safety (PEP 695)
- **PEP 695**: Python Enhancement Proposal para sintaxe de parâmetros de tipo (Python 3.12+)
- **Repository Pattern**: Abstração para acesso a dados que separa lógica de negócio da persistência
- **Unit of Work**: Pattern que gerencia transações atômicas
- **CQRS**: Command Query Responsibility Segregation - separação de operações de leitura e escrita
- **Result Pattern**: Tipo que encapsula sucesso ou falha de operações
- **Specification Pattern**: Pattern para encapsular regras de negócio combináveis
- **Circuit Breaker**: Pattern de resiliência para falhas em serviços externos
- **Rate Limiter**: Controle de taxa de requisições
- **Feature Flag**: Toggle para habilitar/desabilitar funcionalidades
- **Multitenancy**: Arquitetura que suporta múltiplos clientes isolados
- **OpenTelemetry**: Framework de observabilidade para traces, metrics e logs

## Requirements

### Requirement 1: Generic Repository Pattern

**User Story:** As a developer, I want a fully generic repository implementation, so that I can reuse CRUD operations across all entities without code duplication.

#### Acceptance Criteria

1. THE Generic Repository SHALL use PEP 695 type parameter syntax `class IRepository[T, CreateT, UpdateT]`
2. THE Generic Repository SHALL provide async methods for get_by_id, get_all, create, update, delete, exists, and create_many
3. THE SQLModel Repository SHALL extend the generic interface with SQLAlchemy-specific implementation
4. THE In-Memory Repository SHALL provide a test-friendly implementation of the same interface
5. WHEN a new entity is added THEN the system SHALL require only DTO definitions without new repository code

### Requirement 2: Generic Use Case / Service Layer

**User Story:** As a developer, I want generic use cases for business logic, so that I can implement CRUD operations with minimal boilerplate.

#### Acceptance Criteria

1. THE BaseUseCase SHALL use PEP 695 syntax `class BaseUseCase[T, CreateDTO, UpdateDTO, ResponseDTO]`
2. THE BaseUseCase SHALL provide methods for get, list, create, update, delete with automatic DTO mapping
3. THE BaseUseCase SHALL support @overload for type-narrowed return types (raise_on_missing pattern)
4. THE BaseUseCase SHALL integrate with Unit of Work for transaction management
5. WHEN validation is needed THEN the system SHALL allow override of _validate_create and _validate_update hooks

### Requirement 3: Generic Mapper Interface

**User Story:** As a developer, I want generic mappers for entity-DTO conversion, so that I can transform data consistently across the application.

#### Acceptance Criteria

1. THE IMapper SHALL use PEP 695 syntax `class IMapper[Source, Target]`
2. THE IMapper SHALL provide to_dto, to_entity, to_dto_list, and to_entity_list methods
3. THE AutoMapper SHALL automatically map fields with matching names between types
4. THE BaseMapper SHALL support field_mapping configuration for non-matching field names
5. WHEN mapping fails THEN the system SHALL raise MapperError with field and context information

### Requirement 4: Result Pattern for Error Handling

**User Story:** As a developer, I want a Result type for explicit error handling, so that I can avoid exceptions for expected failures.

#### Acceptance Criteria

1. THE Result type SHALL be defined as `type Result[T, E] = Ok[T] | Err[E]`
2. THE Ok class SHALL provide is_ok, unwrap, unwrap_or, and map methods
3. THE Err class SHALL provide is_err, unwrap (raises), unwrap_or, and map_err methods
4. THE Result pattern SHALL use frozen dataclasses with slots for memory efficiency
5. WHEN chaining operations THEN the system SHALL support monadic composition via map and flat_map

### Requirement 5: Generic CQRS Handlers

**User Story:** As a developer, I want generic command and query handlers, so that I can implement CQRS pattern with type safety.

#### Acceptance Criteria

1. THE CommandHandler SHALL use PEP 695 syntax `class CommandHandler[TCommand, TResult]`
2. THE QueryHandler SHALL use PEP 695 syntax `class QueryHandler[TQuery, TResult]`
3. THE handlers SHALL return Result types for explicit error handling
4. THE Command and Query base classes SHALL be immutable Pydantic models
5. WHEN a handler is registered THEN the system SHALL validate type compatibility at registration time

### Requirement 6: Generic Protocol Definitions

**User Story:** As a developer, I want protocol-based interfaces, so that I can achieve loose coupling through structural typing.

#### Acceptance Criteria

1. THE AsyncRepository protocol SHALL define the contract for async data access
2. THE CacheProvider protocol SHALL define get, set, delete, and clear operations
3. THE EventHandler protocol SHALL use `class EventHandler[T]` for typed event handling
4. THE UnitOfWork protocol SHALL define commit, rollback, and context manager methods
5. WHEN implementing a protocol THEN the system SHALL use @runtime_checkable for isinstance checks

### Requirement 7: Generic API Endpoints Factory

**User Story:** As a developer, I want a generic endpoint factory, so that I can generate CRUD routes automatically for any entity.

#### Acceptance Criteria

1. THE GenericEndpoints SHALL use PEP 695 syntax with four type parameters (Entity, Create, Update, Response)
2. THE EndpointFactory SHALL generate create, read, update, delete, and list endpoints
3. THE EndpointConfig SHALL allow enabling/disabling individual operations
4. THE endpoints SHALL support pagination, filtering, and sorting via query parameters
5. WHEN bulk operations are enabled THEN the system SHALL provide bulk_create, bulk_update, and bulk_delete endpoints

### Requirement 8: Generic Pagination Response

**User Story:** As a developer, I want generic pagination DTOs, so that I can return consistent paginated responses.

#### Acceptance Criteria

1. THE PaginatedResponse SHALL use PEP 695 syntax `class PaginatedResponse[T]`
2. THE PaginatedResponse SHALL include items, total, page, size, pages, has_next, and has_previous
3. THE computed fields SHALL calculate pages and navigation flags automatically
4. THE ApiResponse wrapper SHALL use `class ApiResponse[T]` for consistent response format
5. WHEN returning errors THEN the system SHALL use RFC 7807 ProblemDetail format

### Requirement 9: Type Aliases with PEP 695

**User Story:** As a developer, I want modern type aliases, so that I can define reusable types with the new syntax.

#### Acceptance Criteria

1. THE type aliases SHALL use PEP 695 `type` statement syntax
2. THE types module SHALL define FilterDict, SortOrder, QueryParams, Headers aliases
3. THE types module SHALL define JSON type aliases (JSONPrimitive, JSONValue, JSONObject, JSONArray)
4. THE types module SHALL define repository aliases (CRUDRepository, ReadOnlyRepository)
5. THE types module SHALL define callback aliases (AsyncCallback, SyncCallback, EventCallback)

### Requirement 10: Annotated Types for Validation

**User Story:** As a developer, I want annotated types with built-in validation, so that I can enforce constraints declaratively.

#### Acceptance Criteria

1. THE types module SHALL define ULID and UUID types with regex validation
2. THE types module SHALL define string types (NonEmptyStr, TrimmedStr, ShortStr, MediumStr, LongStr, Slug)
3. THE types module SHALL define contact types (Email, PhoneNumber) with pattern validation
4. THE types module SHALL define numeric types (PositiveInt, NonNegativeInt, Percentage)
5. THE types module SHALL define security types (Password, SecurePassword, JWTToken)

### Requirement 11: Generic Specification Pattern

**User Story:** As a developer, I want a generic specification pattern, so that I can compose business rules with type safety.

#### Acceptance Criteria

1. THE Specification SHALL use PEP 695 syntax `class Specification[T]`
2. THE Specification SHALL provide is_satisfied_by method returning bool
3. THE Specification SHALL support AND, OR, NOT composition via operators
4. THE CompositeSpecification SHALL combine multiple specifications
5. WHEN used with repositories THEN the system SHALL translate specifications to query filters

### Requirement 12: Generic Event Sourcing

**User Story:** As a developer, I want generic event sourcing support, so that I can implement event-driven architectures.

#### Acceptance Criteria

1. THE DomainEvent base class SHALL include event_id, timestamp, and aggregate_id
2. THE AggregateRoot SHALL use `class AggregateRoot[IdType]` with event collection
3. THE EventStore protocol SHALL define append and load_stream methods
4. THE event handlers SHALL use `class EventHandler[T: DomainEvent]`
5. WHEN events are applied THEN the system SHALL maintain aggregate consistency

### Requirement 13: Generic Cache Decorator

**User Story:** As a developer, I want a generic cache decorator, so that I can cache function results with type safety.

#### Acceptance Criteria

1. THE cache decorator SHALL preserve function type signatures
2. THE cache decorator SHALL support TTL configuration
3. THE cache decorator SHALL support key generation from function arguments
4. THE CacheProvider protocol SHALL be injectable for different backends (Redis, in-memory)
5. WHEN cache is invalidated THEN the system SHALL support pattern-based invalidation

### Requirement 14: Generic Resilience Patterns

**User Story:** As a developer, I want generic resilience patterns, so that I can handle failures gracefully.

#### Acceptance Criteria

1. THE CircuitBreaker SHALL use generic type for wrapped function return type
2. THE RateLimiter SHALL support configurable limits and windows
3. THE Retry decorator SHALL support exponential backoff with jitter
4. THE Bulkhead pattern SHALL limit concurrent executions
5. WHEN a circuit opens THEN the system SHALL provide fallback mechanism

### Requirement 15: Generic Dependency Injection Container

**User Story:** As a developer, I want a generic DI container, so that I can manage dependencies with type safety.

#### Acceptance Criteria

1. THE Container SHALL support singleton, factory, and transient lifetimes
2. THE Container SHALL resolve dependencies by type with generics
3. THE Container SHALL support provider overriding for testing
4. THE Container SHALL integrate with FastAPI's Depends system
5. WHEN circular dependencies exist THEN the system SHALL detect and report them

### Requirement 16: Generic Middleware Chain

**User Story:** As a developer, I want a generic middleware chain, so that I can compose request processing pipelines.

#### Acceptance Criteria

1. THE Middleware protocol SHALL define async call signature
2. THE MiddlewareChain SHALL compose middlewares in order
3. THE ConditionalMiddleware SHALL apply middleware based on path patterns
4. THE middleware SHALL support request/response transformation
5. WHEN an error occurs THEN the system SHALL propagate through error handling middleware

### Requirement 17: Generic Query Builder

**User Story:** As a developer, I want a generic query builder, so that I can construct type-safe database queries.

#### Acceptance Criteria

1. THE QueryBuilder SHALL use fluent interface pattern
2. THE QueryBuilder SHALL support where, order_by, limit, offset operations
3. THE FilterCondition SHALL support multiple operators (eq, ne, gt, lt, like, in)
4. THE SortCondition SHALL support ascending and descending order
5. WHEN building queries THEN the system SHALL prevent SQL injection via parameterization

### Requirement 18: Generic Feature Flags

**User Story:** As a developer, I want generic feature flag support, so that I can toggle features without deployment.

#### Acceptance Criteria

1. THE FeatureFlag service SHALL support boolean, percentage, and user-based flags
2. THE FeatureFlag decorator SHALL conditionally execute code based on flag state
3. THE FeatureFlag provider SHALL be injectable (in-memory, external service)
4. THE flags SHALL support gradual rollout percentages
5. WHEN a flag is disabled THEN the system SHALL provide fallback behavior

### Requirement 19: Generic Multitenancy Support

**User Story:** As a developer, I want generic multitenancy support, so that I can isolate tenant data.

#### Acceptance Criteria

1. THE TenantContext SHALL provide current tenant information
2. THE TenantMiddleware SHALL extract tenant from request (header, subdomain, path)
3. THE TenantRepository SHALL automatically filter queries by tenant_id
4. THE tenant isolation SHALL support row-level security patterns
5. WHEN tenant is not identified THEN the system SHALL reject the request

### Requirement 20: Generic Background Tasks

**User Story:** As a developer, I want generic background task support, so that I can execute async operations.

#### Acceptance Criteria

1. THE TaskQueue protocol SHALL define enqueue and get_result methods
2. THE Task decorator SHALL register functions as background tasks
3. THE TaskResult SHALL use Result pattern for success/failure
4. THE task system SHALL support retry with exponential backoff
5. WHEN a task fails THEN the system SHALL log and optionally retry

### Requirement 21: Generic Health Checks

**User Story:** As a developer, I want generic health check endpoints, so that I can monitor application health.

#### Acceptance Criteria

1. THE HealthCheck protocol SHALL define check method returning HealthStatus
2. THE HealthEndpoint SHALL aggregate multiple health checks
3. THE health checks SHALL support liveness and readiness probes
4. THE health response SHALL include component status and latency
5. WHEN any check fails THEN the system SHALL return appropriate HTTP status

### Requirement 22: Generic Observability

**User Story:** As a developer, I want generic observability support, so that I can monitor application behavior.

#### Acceptance Criteria

1. THE tracing SHALL integrate with OpenTelemetry for distributed tracing
2. THE metrics SHALL support counters, gauges, and histograms
3. THE logging SHALL include correlation IDs for request tracing
4. THE observability middleware SHALL automatically instrument requests
5. WHEN errors occur THEN the system SHALL capture stack traces with context

### Requirement 23: Generic API Versioning

**User Story:** As a developer, I want generic API versioning, so that I can evolve APIs without breaking clients.

#### Acceptance Criteria

1. THE versioning SHALL support URL path versioning (/v1/, /v2/)
2. THE versioning SHALL support header-based versioning
3. THE version router SHALL route requests to appropriate handlers
4. THE deprecated endpoints SHALL return deprecation warnings
5. WHEN version is not specified THEN the system SHALL use default version

### Requirement 24: Generic Data Export

**User Story:** As a developer, I want generic data export support, so that I can export data in multiple formats.

#### Acceptance Criteria

1. THE DataExporter SHALL use `class DataExporter[T]` for typed exports
2. THE exporter SHALL support CSV, JSON, and Excel formats
3. THE exporter SHALL support streaming for large datasets
4. THE export SHALL respect field visibility and permissions
5. WHEN exporting THEN the system SHALL sanitize sensitive data

### Requirement 25: Code Quality and Architecture Compliance

**User Story:** As a developer, I want architecture validation, so that I can ensure code follows established patterns.

#### Acceptance Criteria

1. THE codebase SHALL have no duplicate code blocks (DRY principle)
2. THE codebase SHALL use Generics for all reusable components
3. THE file sizes SHALL not exceed 400 lines (max 500 with exception)
4. THE function complexity SHALL not exceed 10 (cyclomatic complexity)
5. WHEN patterns are violated THEN the system SHALL fail CI checks
