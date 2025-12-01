# Implementation Plan

## 1. Validate and Enhance Core Generic Components

- [x] 1.1 Audit existing Generic Repository implementation
  - Review `src/core/base/repository.py` for PEP 695 compliance
  - Verify all CRUD methods are async and properly typed
  - Ensure InMemoryRepository matches IRepository interface
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 1.2 Write property test for Repository CRUD Round-Trip
  - **Property 1: Repository CRUD Round-Trip**
  - **Validates: Requirements 1.2, 1.3, 1.4**

- [x] 1.3 Audit existing Generic Use Case implementation
  - Review `src/core/base/use_case.py` for PEP 695 compliance
  - Verify @overload patterns for type narrowing
  - Ensure UnitOfWork integration works correctly
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 1.4 Write property test for Use Case Transaction Atomicity
  - **Property 7: Use Case Transaction Atomicity**
  - **Validates: Requirements 2.4**

- [x] 1.5 Audit existing Generic Mapper implementation
  - Review `src/application/common/mapper.py` for PEP 695 compliance
  - Verify AutoMapper field mapping logic
  - Ensure MapperError provides proper context
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 1.6 Write property test for Mapper Bidirectional Consistency
  - **Property 2: Mapper Bidirectional Consistency**
  - **Validates: Requirements 3.3, 3.4**

## 2. Validate Result Pattern and Error Handling

- [x] 2.1 Audit existing Result Pattern implementation
  - Review `src/core/base/result.py` for PEP 695 compliance
  - Verify Ok and Err classes have all required methods
  - Ensure frozen dataclasses with slots are used
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 2.2 Write property test for Result Pattern Monad Laws
  - **Property 3: Result Pattern Monad Laws**
  - **Validates: Requirements 4.2, 4.3, 4.5**

- [x] 2.3 Audit existing Exception Hierarchy
  - Review `src/core/errors/domain_errors.py` for completeness
  - Verify all exception types have proper error codes and status codes
  - Ensure ErrorContext provides correlation IDs
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5 (from error handling)_

## 3. Validate CQRS and Protocol Definitions

- [x] 3.1 Audit existing CQRS Handlers
  - Review `src/application/common/handlers.py` for PEP 695 compliance
  - Verify CommandHandler and QueryHandler return Result types
  - Ensure Command and Query base classes are immutable
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 3.2 Audit existing Protocol Definitions
  - Review `src/core/protocols/repository.py` for completeness
  - Verify all protocols use @runtime_checkable
  - Ensure generic type parameters are properly defined
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

## 4. Checkpoint - Ensure all tests pass
- Ensure all tests pass, ask the user if questions arise.

## 5. Validate Generic API Components

- [x] 5.1 Audit existing Generic Endpoints Factory
  - Review `src/interface/api/generic_crud/endpoints.py` for PEP 695 compliance
  - Verify EndpointConfig allows enabling/disabling operations
  - Ensure pagination, filtering, sorting work correctly
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 5.2 Audit existing Generic DTOs
  - Review `src/application/common/dto.py` for PEP 695 compliance
  - Verify PaginatedResponse computed fields
  - Ensure ApiResponse wrapper is properly generic
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 5.3 Write property test for Pagination Computation Correctness
  - **Property 4: Pagination Computation Correctness**
  - **Validates: Requirements 8.2, 8.3**

## 6. Validate Type System

- [x] 6.1 Audit existing Type Aliases
  - Review `src/core/types/types.py` for PEP 695 compliance
  - Verify all type aliases use `type` statement syntax
  - Ensure JSON, Repository, Callback aliases are defined
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 6.2 Audit existing Annotated Types
  - Review ULID, UUID, Email, PhoneNumber patterns
  - Verify string, numeric, security types have proper constraints
  - Ensure all types have proper Field descriptions
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 6.3 Write property test for Annotated Type Validation
  - **Property 5: Annotated Type Validation**
  - **Validates: Requirements 10.1, 10.2, 10.3**

## 7. Implement Missing Generic Components

- [x] 7.1 Implement Generic Specification Pattern
  - Create `src/core/base/specification.py` with PEP 695 syntax
  - Implement is_satisfied_by method
  - Add AND, OR, NOT composition operators
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 7.2 Write property test for Specification Boolean Algebra
  - **Property 6: Specification Boolean Algebra**
  - **Validates: Requirements 11.3, 11.4**

- [x] 7.3 Audit existing Event Sourcing components
  - Review `src/core/base/domain_event.py` and `src/core/base/aggregate_root.py`
  - Verify DomainEvent has event_id, timestamp, aggregate_id
  - Ensure AggregateRoot uses generic type with event collection
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

## 8. Checkpoint - Ensure all tests pass
- Ensure all tests pass, ask the user if questions arise.

## 9. Validate Infrastructure Components

- [x] 9.1 Audit existing Cache implementation
  - Review `src/infrastructure/cache/` for decorator patterns
  - Verify TTL configuration support
  - Ensure key generation from arguments works
  - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

- [x] 9.2 Write property test for Cache Decorator Idempotence
  - **Property 8: Cache Decorator Idempotence**
  - **Validates: Requirements 13.1, 13.2, 13.3**

- [x] 9.3 Audit existing Resilience patterns
  - Review `src/infrastructure/resilience/` for circuit breaker, bulkhead
  - Review `src/infrastructure/security/rate_limiter.py` for rate limiting
  - Verify exponential backoff with jitter in retry logic
  - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [x] 9.4 Write property test for Rate Limiter Enforcement
  - **Property 9: Rate Limiter Enforcement**
  - **Validates: Requirements 14.2**

## 10. Validate DI Container and Middleware

- [x] 10.1 Audit existing DI Container
  - Review `src/core/container.py` for lifetime support
  - Verify provider overriding for testing
  - Ensure FastAPI Depends integration
  - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

- [x] 10.2 Audit existing Middleware Chain
  - Review `src/interface/api/middleware/` for composition
  - Verify ConditionalMiddleware path pattern matching
  - Ensure error propagation through middleware
  - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

## 11. Validate Query Builder and Feature Flags

- [x] 11.1 Audit existing Query Builder
  - Review `src/infrastructure/db/query_builder.py` for fluent interface
  - Verify FilterCondition operators (eq, ne, gt, lt, like, in)
  - Ensure SQL injection prevention via parameterization
  - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_

- [x] 11.2 Audit existing Feature Flags
  - Review `src/application/feature_flags/` for flag types
  - Verify percentage rollout support
  - Ensure fallback behavior when flag disabled
  - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5_

## 12. Checkpoint - Ensure all tests pass
- Ensure all tests pass, ask the user if questions arise.

## 13. Validate Multitenancy and Background Tasks

- [x] 13.1 Audit existing Multitenancy support
  - Review `src/application/multitenancy/` for tenant context
  - Verify tenant extraction from request
  - Ensure automatic query filtering by tenant_id
  - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5_

- [x] 13.2 Write property test for Tenant Isolation
  - **Property 10: Tenant Isolation**
  - **Validates: Requirements 19.3, 19.4**

- [x] 13.3 Audit existing Background Tasks
  - Review `src/infrastructure/tasks/` for task queue protocol
  - Verify retry with exponential backoff
  - Ensure Result pattern for task results
  - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5_

## 14. Validate Health Checks and Observability

- [x] 14.1 Audit existing Health Checks
  - Review `src/interface/api/v1/health_router.py` for health endpoints
  - Verify liveness and readiness probe support
  - Ensure component status and latency in response
  - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5_

- [x] 14.2 Write property test for Health Check Aggregation
  - **Property 11: Health Check Aggregation**
  - **Validates: Requirements 21.2, 21.5**

- [x] 14.3 Audit existing Observability
  - Review `src/infrastructure/observability/` for OpenTelemetry integration
  - Verify metrics support (counters, gauges, histograms)
  - Ensure correlation IDs in logging
  - _Requirements: 22.1, 22.2, 22.3, 22.4, 22.5_

## 15. Validate API Versioning and Data Export

- [x] 15.1 Audit existing API Versioning
  - Review `src/interface/api/versioning.py` for URL path versioning
  - Verify header-based versioning support
  - Ensure deprecation warnings for old endpoints
  - _Requirements: 23.1, 23.2, 23.3, 23.4, 23.5_

- [x] 15.2 Write property test for API Versioning Routing
  - **Property 12: API Versioning Routing**
  - **Validates: Requirements 23.1, 23.2, 23.3**

- [x] 15.3 Audit existing Data Export
  - Review `src/application/common/data_export.py` for generic exporter
  - Verify CSV, JSON, Excel format support
  - Ensure streaming for large datasets
  - _Requirements: 24.1, 24.2, 24.3, 24.4, 24.5_

## 16. Code Quality Validation

- [x] 16.1 Run code duplication analysis
  - Use tools like pylint or custom scripts to find duplicate code
  - Refactor duplicates into generic components
  - _Requirements: 25.1_

- [x] 16.2 Verify Generic usage across codebase
  - Ensure all reusable components use PEP 695 Generics
  - Document any exceptions with ADR
  - _Requirements: 25.2_

- [x] 16.3 Validate file sizes and complexity
  - Ensure no file exceeds 400 lines (max 500 with exception)
  - Ensure function complexity does not exceed 10
  - _Requirements: 25.3, 25.4_

## 17. Final Checkpoint - Ensure all tests pass
- Ensure all tests pass, ask the user if questions arise.

## 18. Documentation and Final Review

- [x] 18.1 Update architecture documentation
  - Document all generic components in docs/architecture/
  - Create diagrams showing component relationships
  - _Requirements: All_

- [x] 18.2 Create usage examples
  - Add examples showing how to create new entities with minimal code
  - Document the "zero boilerplate" workflow
  - _Requirements: 1.5, 25.1, 25.2_
