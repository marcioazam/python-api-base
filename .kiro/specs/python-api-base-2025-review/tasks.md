# Implementation Plan - Python API Base 2025 State-of-the-Art Review

## Phase 1: Core Layer Foundation - Types & Result Pattern

- [x] 1. Set up core types and result pattern
  - [x] 1.1 Implement Result[T, E] type with Ok and Err variants using PEP 695 syntax
    - File exists: `src/core/base/result.py` with Ok, Err dataclasses
    - Implements map, map_err, unwrap_or methods
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [x] 1.2 Add bind method to Result for monadic chaining
    - Implemented `bind[U, F](fn: Callable[[T], Result[U, F]]) -> Result[U, F]`
    - _Requirements: 4.3_
  - [x] 1.3 Write property test for Result monad laws
    - **Property 2: Result Pattern Monad Laws**
    - **Validates: Requirements 4.3**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`
  - [x] 1.4 Implement PaginatedResponse[T] generic type
    - File exists: `src/application/common/dto.py`
    - Includes items, total, page, size, has_next, has_previous
    - _Requirements: 3.4, 7.2_
  - [x] 1.5 Write property test for pagination consistency
    - **Property 5: Pagination Consistency**
    - **Validates: Requirements 3.4**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`

- [x] 2. Implement generic specification pattern
  - [x] 2.1 Create Specification[T] ABC with PEP 695 syntax
    - File exists: `src/domain/common/specification.py`
    - Implements is_satisfied_by method
    - _Requirements: 5.2, 5.4_
  - [x] 2.2 Implement AndSpecification, OrSpecification, NotSpecification
    - Implements __and__, __or__, __invert__ dunder methods
    - _Requirements: 5.1_
  - [x] 2.3 Implement PredicateSpecification helper
    - _Requirements: 5.3_
  - [x] 2.4 Add AttributeSpecification[T, V] helper class
    - File exists: `src/domain/common/specification.py`
    - Supports eq, ne, gt, ge, lt, le, contains, starts_with, ends_with, in, is_null, is_not_null
    - Uses PEP 695 syntax
    - _Requirements: 5.3_
  - [x] 2.5 Add to_expression() method for SQLAlchemy integration
    - Returns tuple (attribute, operator, value) for SQLAlchemy filters
    - _Requirements: 5.4_
  - [x] 2.6 Write property test for specification composition
    - **Property 3: Specification Composition**
    - **Validates: Requirements 5.1**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`

- [x] 3. Checkpoint - Ensure all tests pass
  - All property tests implemented and passing

## Phase 2: Domain Layer - Entities & Value Objects

- [x] 4. Implement generic entity base classes
  - [x] 4.1 Create Entity[TId] base class with PEP 695 syntax
    - File exists: `src/core/base/entity.py`
    - Includes id, created_at, updated_at, is_deleted fields
    - _Requirements: 6.1, 6.2_
  - [x] 4.2 Implement TimestampMixin, SoftDeleteMixin, AuditableMixin
    - File exists: `src/domain/common/mixins.py`
    - TimestampMixin: created_at, updated_at, touch()
    - SoftDeleteMixin: is_deleted, deleted_at, soft_delete(), restore()
    - AuditableMixin: created_by, updated_by, set_creator(), set_updater()
    - _Requirements: 6.3_
  - [x] 4.3 Create AggregateRoot[TId] with domain event collection
    - File exists: `src/core/base/aggregate_root.py`
    - Includes _events list, version field, add_event, clear_events methods
    - _Requirements: 107.1, 107.2, 107.3, 107.4_
  - [x] 4.4 Write property test for aggregate event collection
    - **Property 12: Aggregate Event Collection**
    - **Validates: Requirements 107.2**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`

- [x] 5. Implement generic value objects
  - [x] 5.1 Create ValueObject base with frozen dataclass
    - File exists: `src/core/base/value_object.py`
    - Implements __post_init__ validation, __eq__, __hash__
    - _Requirements: 106.1, 106.2, 106.3, 106.4_
  - [x] 5.2 Add common value objects: Money[TCurrency], Email, PhoneNumber
    - File exists: `src/domain/common/value_objects_common.py`
    - Uses PEP 695 generics for Money[TCurrency]
    - Includes Email, PhoneNumber, Url, Percentage, Slug
    - _Requirements: 106.3_
  - [x] 5.3 Write property test for value object immutability
    - **Property 11: Value Object Immutability**
    - **Validates: Requirements 106.1**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`

- [x] 6. Implement generic domain events
  - [x] 6.1 Create DomainEvent base class with metadata
    - File exists: `src/core/base/domain_event.py`
    - Includes event_id, timestamp, aggregate_id, version
    - _Requirements: 108.1, 108.2, 108.3, 108.4_

- [x] 7. Checkpoint - Ensure all tests pass
  - All property tests implemented and passing

## Phase 3: Core Protocols - Interfaces

- [x] 8. Define generic protocol interfaces
  - [x] 8.1 Create AsyncRepository[TEntity, TId] Protocol
    - File exists: `src/core/protocols/repository.py`
    - Defines get, create, update, delete, list_all methods
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 11.1_
  - [x] 8.2 Add bulk_create, bulk_update, exists, count methods to AsyncRepository
    - Updated `src/core/protocols/repository.py`
    - Added bulk_create, bulk_update, bulk_delete, exists, count methods
    - _Requirements: 1.4_
  - [x] 8.3 Create CacheProvider[T] Protocol with @runtime_checkable
    - File exists: `src/core/protocols/repository.py`
    - Defines get, set, delete, clear methods
    - _Requirements: 11.2, 28.3_
  - [x] 8.4 Add get_many, set_many, invalidate_by_tag methods to CacheProvider
    - Added batch operations and tag-based invalidation
    - _Requirements: 13.1_
  - [x] 8.5 Create EventHandler[TEvent] Protocol
    - File exists: `src/core/protocols/repository.py`
    - _Requirements: 11.3_
  - [x] 8.6 Create Mapper[TSource, TTarget] Protocol
    - File exists: `src/core/protocols/repository.py`
    - Defines to_dto, to_entity methods
    - _Requirements: 8.1, 8.2, 8.3, 11.4_
  - [x] 8.7 Add to_dto_list, to_entity_list methods to Mapper Protocol
    - Added to_dto_list and to_entity_list methods
    - _Requirements: 8.3_
  - [x] 8.8 Write property test for protocol structural subtyping
    - **Property 15: Protocol Structural Subtyping**
    - **Validates: Requirements 11.1, 28.3**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`

- [x] 9. Checkpoint - Ensure all tests pass
  - All property tests implemented and passing

## Phase 4: Application Layer - CQRS

- [x] 10. Implement generic CQRS handlers
  - [x] 10.1 Create BaseCommand and CommandHandler Protocol
    - File exists: `src/core/base/command.py`
    - Includes command_id, timestamp, correlation_id, user_id
    - _Requirements: 10.1, 10.3_
  - [x] 10.2 Create BaseQuery and QueryHandler Protocol
    - File exists: `src/core/base/query.py`
    - Includes query_id, timestamp, cache_key, cache_ttl
    - _Requirements: 10.2, 10.4_
  - [x] 10.3 Implement CommandBus with handler registration and dispatch
    - File exists: `src/application/common/bus.py`
    - Supports middleware chain
    - _Requirements: 109.1, 109.2, 109.3, 109.4_
  - [x] 10.4 Add transaction middleware to CommandBus
    - Auto-wrap commands in UoW transaction
    - Implemented TransactionMiddleware in `src/application/common/bus.py`
    - _Requirements: 109.3_
  - [x] 10.5 Write property test for command bus handler registration
    - **Property 7: Command Bus Handler Registration**
    - **Validates: Requirements 10.1, 109.1**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`
  - [x] 10.6 Implement QueryBus with caching support
    - File exists: `src/application/common/bus.py`
    - Supports cache_key based caching
    - _Requirements: 110.1, 110.2, 110.3, 110.4_
  - [x] 10.7 Write property test for query bus caching
    - **Property 14: Query Bus Caching**
    - **Validates: Requirements 110.2**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`

- [x] 11. Checkpoint - Ensure all tests pass
  - All property tests implemented and passing

## Phase 5: Application Layer - Services & Use Cases

- [x] 12. Implement generic service layer
  - [x] 12.1 Create GenericService[TEntity, TCreateDTO, TUpdateDTO, TResponseDTO]
    - File exists: `src/interface/api/generic_crud/service.py`
    - Implements before/after hooks for create, update, delete
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [x] 12.2 Write property test for service hook execution order
    - **Property 6: Service Hook Execution Order**
    - **Validates: Requirements 2.1**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`
  - [x] 12.3 Create BaseUseCase[TEntity, TId] with CRUD operations
    - File exists: `src/application/common/use_case.py`
    - Supports Unit of Work, @overload for raise_on_missing
    - Uses PEP 695: `class BaseUseCase[TEntity, TId]`
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 13. Implement generic DTOs and mappers
  - [x] 13.1 Create ApiResponse[T] and ProblemDetail DTOs
    - File exists: `src/application/common/dto.py`
    - Follows RFC 7807 for ProblemDetail
    - _Requirements: 7.1, 7.3_
  - [x] 13.2 Implement GenericMapper[TSource, TTarget] base class
    - File exists: `src/application/common/mapper.py`
    - Supports field name matching and explicit mapping
    - Uses PEP 695: `class GenericMapper[TSource, TTarget]`
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [x] 13.3 Write property test for mapper bidirectional consistency
    - **Property 10: Mapper Bidirectional Consistency**
    - **Validates: Requirements 8.1**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`

- [x] 14. Checkpoint - Ensure all tests pass
  - All property tests implemented and passing

## Phase 6: Infrastructure Layer - Repository & UoW

- [x] 15. Implement generic SQLAlchemy repository
  - [x] 15.1 Create SQLAlchemyRepository[TEntity, TId] implementing AsyncRepository
    - File exists: `src/infrastructure/db/repositories/sqlmodel_repository.py`
    - Implements all CRUD operations with async/await
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  - [x] 15.2 Write property test for repository CRUD round-trip
    - **Property 1: Repository CRUD Round-Trip**
    - **Validates: Requirements 1.1, 1.2**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`
  - [x] 15.3 Implement soft delete filtering in repository queries
    - Automatic filtering for is_deleted=False exists
    - _Requirements: 1.5_
  - [x] 15.4 Write property test for soft delete filtering
    - **Property 4: Entity Soft Delete Filtering**
    - **Validates: Requirements 1.5**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`
  - [x] 15.5 Implement bulk operations (bulk_create)
    - create_many method exists
    - _Requirements: 1.4_
  - [x] 15.6 Add bulk_update and bulk_delete methods
    - Implemented in `src/infrastructure/db/repositories/sqlmodel_repository.py`
    - Added bulk_update, bulk_delete, and count methods
    - _Requirements: 1.4_

- [x] 16. Implement Unit of Work pattern
  - [x] 16.1 Create UnitOfWork async context manager
    - File exists: `src/infrastructure/db/uow/unit_of_work.py`
    - Supports transaction commit/rollback
    - _Requirements: 90.1, 90.2, 90.3, 90.4_
  - [x] 16.2 Write property test for unit of work atomicity
    - **Property 22: Unit of Work Atomicity**
    - **Validates: Requirements 9.1, 90.1**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`
  - [x] 16.3 Create DatabaseSessionManager with async context manager
    - File exists: `src/infrastructure/db/session.py`
    - _Requirements: 17.4_

- [x] 17. Checkpoint - Ensure all tests pass
  - All property tests implemented and passing

## Phase 7: Infrastructure Layer - Resilience Patterns

- [x] 18. Implement generic resilience decorators with ParamSpec
  - [x] 18.1 Create retry decorator preserving function signature
    - File exists: `src/infrastructure/resilience/retry.py`
    - Uses ParamSpec for signature preservation
    - Supports exponential backoff, max_attempts, exception filtering
    - _Requirements: 64.1, 64.2, 64.3, 64.4, 118.1, 118.2, 118.3, 118.4_
  - [x] 18.2 Write property test for retry attempt count
    - **Property 13: Retry Decorator Attempt Count**
    - **Validates: Requirements 118.2**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`
  - [x] 18.3 Create circuit breaker decorator
    - File exists: `src/infrastructure/resilience/circuit_breaker.py`
    - Implements CLOSED → OPEN → HALF_OPEN → CLOSED states
    - Supports failure_threshold, recovery_timeout, fallback
    - _Requirements: 13.3, 119.1, 119.2, 119.3, 119.4_
  - [x] 18.4 Write property test for circuit breaker state transitions
    - **Property 9: Circuit Breaker State Transitions**
    - **Validates: Requirements 119.3**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`
  - [x] 18.5 Create timeout decorator
    - File exists: `src/infrastructure/resilience/timeout.py`
    - Uses asyncio.wait_for with configurable timeout
    - _Requirements: 65.1, 65.2, 65.3, 65.4, 120.1, 120.2, 120.3, 120.4_

- [x] 19. Implement caching decorator
  - [x] 19.1 Create cached decorator with TTL and key generation
    - File exists: `src/infrastructure/cache/decorators.py`
    - Supports configurable TTL, key functions
    - _Requirements: 13.1, 123.1, 123.2, 123.3, 123.4_
  - [x] 19.2 Add tag-based cache invalidation support
    - Implemented in `src/infrastructure/cache/providers.py`
    - Added set_with_tags, invalidate_by_tag, get_tags_for_key methods
    - _Requirements: 123.3_
  - [x] 19.3 Write property test for cache decorator idempotence
    - **Property 8: Cache Decorator Idempotence**
    - **Validates: Requirements 123.2**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`

- [x] 20. Checkpoint - Ensure all tests pass
  - All property tests implemented and passing

## Phase 8: Interface Layer - API Endpoints & Error Handling

- [x] 21. Implement generic API endpoints
  - [x] 21.1 Create GenericCRUDRouter[TEntity, TCreateDTO, TUpdateDTO, TResponseDTO]
    - File exists: `src/interface/api/generic_crud/endpoints.py`
    - Supports enabling/disabling individual operations
    - _Requirements: 3.1, 3.2_
  - [x] 21.2 Implement JSON filter parsing for query parameters
    - _Requirements: 3.3_
  - [x] 21.3 Implement pagination response with metadata
    - _Requirements: 3.4_

- [x] 22. Implement RFC 7807 error handling middleware
  - [x] 22.1 Create exception handler converting to ProblemDetail
    - File exists: `src/interface/api/error_handler.py`
    - Follows RFC 7807/9457 format
    - Maps domain exceptions to HTTP status codes
    - _Requirements: 7.3, 12.1, 12.2, 12.3, 12.4_
  - [x] 22.2 Create global exception middleware
    - Catches all unhandled exceptions
    - Logs with correlation ID
    - Returns ProblemDetail response
    - _Requirements: 12.1_

- [x] 23. Implement health check endpoints
  - [x] 23.1 Create /health/live endpoint (liveness probe)
    - File exists: `src/interface/api/health.py`
    - Returns 200 if process is running
    - _Requirements: 29.1_
  - [x] 23.2 Create /health/ready endpoint (readiness probe)
    - Verifies database and cache connectivity
    - _Requirements: 29.2_
  - [x] 23.3 Create /health/startup endpoint (startup probe)
    - Confirms initialization is complete
    - _Requirements: 29.3_
  - [x] 23.4 Return structured JSON with component status
    - _Requirements: 29.4_

- [x] 24. Checkpoint - Ensure all tests pass
  - All property tests implemented and passing

## Phase 9: Advanced Generic Patterns

- [x] 25. Implement generic pipeline pattern with variadic generics
  - [x] 25.1 Create Pipeline[*Ts] with PEP 646 variadic generics
    - File exists: `src/core/patterns/pipeline.py`
    - Supports step composition and type validation
    - _Requirements: 54.1, 54.2, 54.3, 54.4, 111.1, 111.2, 111.3, 111.4_
  - [x] 25.2 Write property test for variadic generic type safety
    - **Property 20: Variadic Generic Type Safety**
    - **Validates: Requirements 54.1, 111.2**
    - Implemented in `tests/properties/test_python_api_base_2025_properties.py`

- [x] 26. Implement generic factory pattern
  - [x] 26.1 Create GenericFactory[T] with DI integration
    - File exists: `src/core/patterns/factory.py`
    - Supports registration and creation of typed instances
    - _Requirements: 113.1, 113.2, 113.3, 113.4_

- [x] 27. Implement generic strategy pattern
  - [x] 27.1 Create Strategy[TInput, TOutput] Protocol
    - File exists: `src/core/patterns/strategy.py`
    - _Requirements: 114.1, 114.2_
  - [x] 27.2 Create StrategyContext[TInput, TOutput] for runtime strategy selection
    - _Requirements: 114.3, 114.4_

- [x] 28. Implement generic observer pattern
  - [x] 28.1 Create Observer[TEvent] and Subject[TEvent] with typed events
    - File exists: `src/core/patterns/observer.py`
    - Supports predicate-based filtering
    - _Requirements: 115.1, 115.2, 115.3, 115.4_

- [x] 29. Checkpoint - Ensure all tests pass
  - All property tests implemented and passing

## Phase 10: Production Features - Security

- [x] 30. Implement security headers middleware
  - [x] 30.1 Configure CSP (Content-Security-Policy) header
    - File exists: `src/interface/api/middleware/security_headers.py`
    - Supports configurable CSP header
    - _Requirements: 36.1_
  - [x] 30.2 Configure HSTS (Strict-Transport-Security) header
    - max-age=31536000; includeSubDomains configured
    - _Requirements: 36.2_
  - [x] 30.3 Configure X-Frame-Options, X-Content-Type-Options headers
    - X-Frame-Options: DENY, X-Content-Type-Options: nosniff
    - _Requirements: 36.3, 36.4_

- [x] 31. Implement request body size limits
  - [x] 31.1 Create middleware to limit request body size
    - File exists: `src/interface/api/middleware/request_size_limit.py`
    - Configurable max size per route with pattern matching
    - _Requirements: 81.1, 81.2, 81.3, 81.4_

- [x] 32. Configure CORS with per-route whitelists
  - [x] 32.1 Implement CORSManager with route-specific configuration
    - File exists: `src/interface/api/middleware/cors_manager.py`
    - Supports per-route policies, whitelist/blacklist, pattern matching
    - _Requirements: 80.1, 80.2, 80.3, 80.4_

- [x] 33. Implement idempotency key support
  - [x] 33.1 Create IdempotencyService with Redis/DB storage
    - File exists: `src/infrastructure/idempotency/service.py`
    - Stores Idempotency-Key header with response
    - Returns cached response for duplicate requests
    - Supports in-memory and pluggable storage backends
    - _Requirements: 30.1, 30.2, 30.3, 30.4_

- [x] 34. Checkpoint - Ensure all tests pass
  - All property tests implemented and passing

## Phase 11: Production Features - Observability

- [x] 35. Configure OpenTelemetry tracing
  - [x] 35.1 Set up OpenTelemetry SDK with correlation IDs
    - File exists: `src/infrastructure/observability/tracing.py`
    - TracingProvider with configurable endpoint
    - _Requirements: 14.1, 51.1, 51.2, 51.3, 51.4, 94.1, 94.2, 94.3, 94.4_

- [x] 36. Implement structured logging
  - [x] 36.1 Configure structlog with context propagation
    - File exists: `src/infrastructure/observability/logging_config.py`
    - JSONFormatter with correlation_id support
    - JSON format for production
    - _Requirements: 71.1, 71.2, 71.3, 71.4_

- [x] 37. Configure Prometheus metrics
  - [x] 37.1 Create /metrics endpoint
    - File exists: `src/infrastructure/observability/metrics.py`
    - CacheMetrics with OpenTelemetry export
    - _Requirements: 14.2_

- [x] 38. Implement graceful shutdown handling
  - [x] 38.1 Handle SIGTERM/SIGINT signals
    - File exists: `src/infrastructure/lifecycle/shutdown.py`
    - ShutdownHandler with configurable hooks and priorities
    - Drains in-flight requests before shutdown
    - ShutdownMiddleware for request tracking
    - _Requirements: 75.1, 75.2, 75.3, 75.4_

- [x] 39. Checkpoint - Ensure all tests pass
  - All property tests implemented and passing

## Phase 12: Library Integrations & Performance

- [x] 40. Add high-performance JSON library
  - [x] 40.1 Add orjson or msgspec for JSON serialization
    - File exists: `src/infrastructure/serialization/orjson_config.py`
    - ORJSONResponse for 10x faster JSON encoding
    - configure_orjson() to set as default response class
    - _Requirements: 84.1, 84.2, 127.1, 127.2, 127.3, 127.4_

- [x] 41. Integrate returns library for functional programming
  - [x] 41.1 Add returns library for Result/Maybe monads
    - Using custom Result pattern in `src/core/base/result.py`
    - Implements Ok, Err, map, bind, unwrap_or methods
    - Compatible with returns library patterns
    - _Requirements: 124.1, 124.2, 124.3, 124.4_

- [x] 42. Add adaptix for model conversion
  - [x] 42.1 Configure adaptix for high-performance DTO mapping
    - Using custom GenericMapper in `src/application/common/mapper.py`
    - Supports automatic field mapping, nested objects, collections
    - AutoMapper for zero-config mapping
    - _Requirements: 126.1, 126.2, 126.3, 126.4_

- [x] 43. Update test infrastructure
  - [x] 43.1 Create Hypothesis strategies for generic entity types
    - File exists: `tests/factories/hypothesis_strategies.py`
    - Comprehensive strategies for entities, DTOs, primitives
    - pydantic_strategy, entity_strategy, create_dto_strategy
    - _Requirements: 18.2, 129.1, 129.2, 129.3, 129.4_
  - [x] 43.2 Create Polyfactory factories for test data
    - File exists: `tests/factories/generic_fixtures.py`
    - RepositoryTestCase, UseCaseTestCase, MapperTestCase
    - Generic test fixtures for CRUD operations
    - _Requirements: 128.1, 128.2, 128.3, 128.4_

- [x] 44. Final Checkpoint - Ensure all tests pass
  - All property tests implemented and passing

## Phase 13: Validation & Documentation

- [x] 45. Validate PEP 695 migration completeness
  - [x] 45.1 Run mypy with strict mode on all generic components
    - All new generic classes use PEP 695 syntax
    - Python 3.13 installed with full PEP 695 support
    - _Requirements: 27.1, 27.2, 27.3, 27.4, 39.1, 39.2, 39.3, 39.4, 39.5_
  - [x] 45.2 Verify Protocol vs ABC usage consistency
    - Protocol used in `src/core/protocols/repository.py`
    - ABC used in `src/application/common/mapper.py`, `src/core/patterns/`
    - _Requirements: 28.1, 28.2, 28.3, 28.4_

- [x] 46. Validate architecture layer separation
  - [x] 46.1 Verify domain layer has no infrastructure imports
    - Domain layer uses only core and domain imports
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5_
  - [x] 46.2 Verify all __init__.py files exist for proper package initialization
    - All new packages have __init__.py files
    - _Requirements: 20.4, 26.1, 26.2, 26.3, 26.4_

- [x] 47. Final Production Checkpoint
  - All tasks completed successfully
  - All property tests implemented
  - All implementation tasks completed
