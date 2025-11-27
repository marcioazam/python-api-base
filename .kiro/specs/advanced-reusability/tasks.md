# Implementation Plan

## Phase 1: Protocol-Based Interfaces

- [x] 1. Implement Protocol definitions

  - [x] 1.1 Create `src/my_api/shared/protocols.py` with core Protocols

    - Define `Identifiable`, `Timestamped`, `SoftDeletable` Protocols
    - Define `AsyncRepository` Protocol with generic type parameters
    - Define `CacheProvider` Protocol
    - Define `EventHandler`, `Command`, `Query` Protocols
    - Use `@runtime_checkable` decorator for runtime isinstance checks
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.2 Write property test for Protocol runtime checking

    - **Property 1: Protocol Runtime Checkable**
    - **Validates: Requirements 1.2, 1.3**

## Phase 2: Advanced Specification Pattern

- [x] 2. Implement Advanced Specification with SQL generation

  - [x] 2.1 Create `src/my_api/shared/advanced_specification.py`

    - Define `ComparisonOperator` enum (eq, ne, gt, lt, ge, le, in, like, between, is_null)
    - Implement `FilterCriteria` dataclass
    - Implement `BaseSpecification` abstract class extending existing Specification
    - Implement `FieldSpecification` with operator evaluation
    - Implement `CompositeSpecification` for AND/OR
    - Implement `NotSpecification` for negation
    - Implement `to_sql_condition()` for SQLAlchemy integration
    - _Requirements: 2.1, 2.2, 2.3, 2.6_

  - [x] 2.2 Create `SpecificationBuilder` for fluent API

    - Implement `where()`, `and_where()`, `or_where()` methods
    - Implement `build()` method returning final specification
    - _Requirements: 2.4_

  - [x] 2.3 Write property tests for Specification pattern

    - **Property 2: Specification Operator Correctness**
    - **Property 3: Specification Composition**
    - **Property 4: Specification Negation**
    - **Validates: Requirements 2.1, 2.2, 2.6**

  - [x] 2.4 Write property test for SQL equivalence

    - **Property 5: Specification SQL Equivalence**
    - **Validates: Requirements 2.3, 2.4**

- [x] 3. Checkpoint - Ensure all tests pass
  - All Phase 1 and 2 tests passing

## Phase 3: Multi-Level Caching System

- [x] 4. Implement Caching Infrastructure

  - [x] 4.1 Create `src/my_api/shared/caching.py`

    - Define `CacheConfig` dataclass with ttl, max_size, key_prefix
    - Define `CacheEntry` dataclass with expiration logic
    - Implement `InMemoryCacheProvider` with LRU eviction
    - Implement async lock for thread safety
    - _Requirements: 3.1, 3.4_

  - [x] 4.2 Implement `RedisCacheProvider`

    - Connect to Redis using redis.asyncio
    - Implement JSON serialization for complex objects
    - Handle connection errors gracefully (log warning, continue without cache)
    - _Requirements: 3.1, 3.6, 3.7_

  - [x] 4.3 Implement `@cached` decorator

    - Support configurable TTL
    - Support custom key generation function
    - Support cache provider injection
    - _Requirements: 3.5_

  - [x] 4.4 Write property tests for caching

    - **Property 6: Cache Round-Trip**
    - **Property 7: Cache TTL Expiration**
    - **Property 8: Cache LRU Eviction**
    - **Property 9: Cached Decorator Idempotence**
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.7**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 4: OpenTelemetry Observability

- [x] 6. Implement OpenTelemetry Integration

  - [x] 6.1 Create `src/my_api/infrastructure/observability/telemetry.py`

    - Initialize TracerProvider with OTLP exporter
    - Initialize MeterProvider with OTLP exporter
    - Configure resource attributes (service.name, service.version)
    - _Requirements: 4.1, 4.6_

  - [x] 6.2 Implement `@traced` decorator

    - Create spans with configurable name and attributes
    - Record exceptions as span events
    - Support async and sync functions
    - _Requirements: 4.5_

  - [x] 6.3 Create `TracingMiddleware` for HTTP requests

    - Extract/inject trace context from headers
    - Record request method, path, status code
    - Measure request duration
    - _Requirements: 4.2, 4.3_

  - [x] 6.4 Integrate trace context with structured logging

    - Add trace_id and span_id to log records
    - Configure structlog processor for OTel context
    - _Requirements: 4.7_

  - [x] 6.5 Write property tests for observability

    - **Property 10: Trace Span Creation**
    - **Property 11: Log Trace Correlation**
    - **Validates: Requirements 4.2, 4.5, 4.7**

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 5: CQRS Pattern

- [x] 8. Implement CQRS Infrastructure

  - [x] 8.1 Create `src/my_api/shared/cqrs.py`

    - Define `Command` abstract base class with `execute()` method
    - Define `Query` abstract base class with `execute()` method
    - Define `CommandHandler` and `QueryHandler` Protocols
    - _Requirements: 5.1, 5.2_

  - [x] 8.2 Implement `CommandBus`

    - Register handlers by command type
    - Dispatch commands to registered handlers
    - Support middleware for cross-cutting concerns
    - Emit domain events after successful command execution
    - _Requirements: 5.3, 5.5_

  - [x] 8.3 Implement `QueryBus`

    - Register handlers by query type
    - Dispatch queries to registered handlers
    - Support caching of query results
    - _Requirements: 5.4_

  - [x] 8.4 Write property tests for CQRS

    - **Property 12: Command Bus Dispatch**
    - **Property 13: Query Bus Dispatch**
    - **Validates: Requirements 5.3, 5.4**

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 6: Enhanced Code Generator

- [x] 10. Enhance Code Generator

  - [x] 10.1 Update `scripts/generate_entity.py`

    - Add `--with-events` flag for domain event generation
    - Add `--with-cache` flag for cache decorator generation
    - Generate property-based tests alongside unit tests
    - _Requirements: 6.5, 6.6_

  - [x] 10.2 Create templates for generated code

    - Template for entity with validators
    - Template for repository with cache support
    - Template for property tests
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 10.3 Write property test for code generation

    - **Property 14: Code Generation Completeness**
    - **Validates: Requirements 6.1, 6.4**

- [x] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 7: Health Checks and Configuration Enhancements

- [x] 12. Health Check Enhancements

  - [x] 12.1 Health endpoints implemented

    - `/health/live` endpoint exists (liveness probe)
    - `/health/ready` endpoint exists (readiness probe)
    - Dependency checks implemented (database, redis)
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 12.2 Add configurable timeout and metrics emission

    - Add configurable timeout for health checks (default 5s)
    - Emit metrics on health status changes
    - _Requirements: 7.4, 7.5_

  - [x] 12.3 Write property tests for health checks

    - **Property 15: Health Check Dependency Verification**
    - **Validates: Requirements 7.2, 7.3**

- [x] 13. Configuration Validation

  - [x] 13.1 Configuration validation implemented

    - Validation for configuration fields exists in config.py
    - SecretStr values used for sensitive data
    - Property tests exist in test_config_properties.py
    - _Requirements: 8.1, 8.2, 8.5_

  - [x] 13.2 Implement `--generate-config-docs` CLI command

    - Output markdown documentation of all settings
    - Script exists at scripts/generate_config_docs.py
    - _Requirements: 8.3_

  - [x] 13.3 Secret redaction verified

    - SecretStr automatically redacts values in string representation
    - **Property 17: Secret Redaction** - inherent in Pydantic SecretStr
    - **Validates: Requirements 8.4, 8.5**

- [x] 14. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 8: Integration and Documentation

- [x] 15. Integration and Wiring

  - [x] 15.1 Update `src/my_api/core/container.py`

    - Register cache providers (InMemoryCacheProvider, RedisCacheProvider)
    - Register CQRS buses (CommandBus, QueryBus)
    - Configure telemetry provider
    - _Requirements: All_

  - [x] 15.2 Update `src/my_api/main.py`

    - Add TracingMiddleware to middleware stack
    - Initialize OpenTelemetry on startup
    - Configure graceful shutdown for telemetry
    - _Requirements: 4.1_

- [x] 16. Documentation



  - [x] 16.1 Update `docs/architecture.md`



    - Document new patterns (Protocols, Specifications, CQRS)
    - Add diagrams for caching and observability
    - _Requirements: All_

  - [x] 16.2 Update `README.md`



    - Add usage examples for new features
    - Document configuration options
    - _Requirements: All_

- [x] 17. Final Checkpoint - Ensure all tests pass


  - Ensure all tests pass, ask the user if questions arise.
