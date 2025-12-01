# Implementation Plan

## Phase 1: Core Generics Consolidation

- [ ] 1. Standardize Type Parameter Naming
  - [ ] 1.1 Audit all generic definitions in src/core/ for naming consistency
    - Review entity.py, repository.py, result.py, patterns/generics.py
    - Document current naming patterns
    - _Requirements: 1.1, 1.2, 1.3_
  - [ ] 1.2 Update handlers.py to use PEP 695 syntax instead of Generic[T, U]
    - Replace `class CommandHandler(ABC, Generic[TCommand, TResult])` with `class CommandHandler[TCommand, TResult](ABC)`
    - _Requirements: 1.4_
  - [ ] 1.3 Write property test for type parameter consistency
    - **Property 14: Validation Result Consistency**
    - **Validates: Requirements 2.4**

- [ ] 2. Consolidate Result Pattern Usage
  - [ ] 2.1 Verify all use cases return Result[T, E] instead of raising exceptions
    - Review use_case.py, create_user.py, item_commands.py
    - _Requirements: 3.1_
  - [ ] 2.2 Write property test for Result round-trip
    - **Property 1: Result Pattern Round-Trip**
    - **Validates: Requirements 3.1, 3.2**
  - [ ] 2.3 Write property test for Result monadic laws
    - **Property 2: Result Monadic Laws**
    - **Validates: Requirements 3.2**

- [ ] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 2: DTO and Response Consolidation

- [ ] 4. Verify Generic DTO Computed Properties
  - [ ] 4.1 Review PaginatedResponse computed properties (pages, has_next, has_previous)
    - Verify edge cases: total=0, page=1, size=1
    - _Requirements: 5.1_
  - [ ] 4.2 Write property test for PaginatedResponse
    - **Property 3: PaginatedResponse Computed Properties**
    - **Validates: Requirements 5.1**
  - [ ] 4.3 Write property test for BatchResult success rate
    - **Property 4: BatchResult Success Rate**
    - **Validates: Requirements 5.3, 22.3**

- [ ] 5. Standardize Error Response Patterns
  - [ ] 5.1 Consolidate error codes into Enums where using strings
    - Review UploadError, TaskStatus, HealthStatus, AuthorizationResult
    - _Requirements: 14.2, 14.3_
  - [ ] 5.2 Create centralized error messages module if not exists
    - _Requirements: 14.1, 14.4_

## Phase 3: Repository Pattern Consolidation

- [ ] 6. Verify Repository Interface Consistency
  - [ ] 6.1 Audit IRepository implementations for interface compliance
    - Check InMemoryRepository, TenantRepository, BatchRepository
    - _Requirements: 6.1_
  - [ ] 6.2 Verify pagination support (offset and cursor-based)
    - Review get_all and get_page methods
    - _Requirements: 6.2_
  - [ ] 6.3 Write property test for Repository CRUD consistency
    - **Property 5: Repository CRUD Consistency**
    - **Validates: Requirements 6.1, 6.2**
  - [ ] 6.4 Write property test for soft delete behavior
    - **Property 6: Repository Soft Delete**
    - **Validates: Requirements 6.4**

- [ ] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 4: Event and Messaging Consolidation

- [ ] 8. Consolidate Event Handler Patterns
  - [ ] 8.1 Audit EventHandler protocols across modules
    - Compare event_bus.py, messaging/generics.py, infrastructure patterns
    - Identify duplicates and consolidate
    - _Requirements: 8.1_
  - [ ] 8.2 Verify TypedEventBus subscription and delivery
    - _Requirements: 8.2_
  - [ ] 8.3 Write property test for EventBus delivery
    - **Property 9: EventBus Delivery**
    - **Validates: Requirements 8.1, 8.2**
  - [ ] 8.4 Write property test for EventBus error isolation
    - **Property 10: EventBus Error Isolation**
    - **Validates: Requirements 8.3**

## Phase 5: Cache Pattern Consolidation

- [ ] 9. Verify Cache Provider Implementations
  - [ ] 9.1 Review InMemoryCacheProvider and RedisCacheProvider
    - Verify CacheProvider[T] protocol compliance
    - _Requirements: 9.2_
  - [ ] 9.2 Verify tag-based invalidation implementation
    - Review set_with_tags and invalidate_by_tag methods
    - _Requirements: 9.4_
  - [ ] 9.3 Write property test for cache round-trip
    - **Property 7: Cache Round-Trip**
    - **Validates: Requirements 9.2, 9.3**
  - [ ] 9.4 Write property test for tag invalidation
    - **Property 8: Cache Tag Invalidation**
    - **Validates: Requirements 9.4**

- [ ] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 6: HTTP Client and Retry Patterns

- [ ] 11. Verify HTTP Client Generics
  - [ ] 11.1 Review HttpRequest[TBody] and HttpResponse[TBody] usage
    - _Requirements: 10.1, 10.2_
  - [ ] 11.2 Verify RetryPolicy implementations (ExponentialBackoff, LinearBackoff)
    - _Requirements: 10.3_
  - [ ] 11.3 Write property test for retry policy backoff
    - **Property 12: Retry Policy Backoff**
    - **Validates: Requirements 10.3**
  - [ ] 11.4 Verify RequestBuilder fluent API
    - _Requirements: 10.4_

## Phase 7: Security Pattern Consolidation

- [ ] 12. Verify Authorization and Rate Limiting
  - [ ] 12.1 Review AuthorizationContext[TResource, TAction] usage
    - _Requirements: 13.1_
  - [ ] 12.2 Review RateLimiter[TKey] implementations
    - Check SlidingWindowLimiter and TokenBucketLimiter
    - _Requirements: 13.3_
  - [ ] 12.3 Write property test for rate limiter enforcement
    - **Property 11: Rate Limiter Enforcement**
    - **Validates: Requirements 13.3**

## Phase 8: Multitenancy Pattern Consolidation

- [ ] 13. Verify Tenant Isolation
  - [ ] 13.1 Review TenantRepository query filtering
    - Verify _apply_tenant_filter is called on all queries
    - _Requirements: 20.1_
  - [ ] 13.2 Review TenantContext context manager
    - Verify set/clear of tenant context
    - _Requirements: 20.2_
  - [ ] 13.3 Write property test for tenant context isolation
    - **Property 13: TenantContext Isolation**
    - **Validates: Requirements 20.1, 20.2**
  - [ ] 13.4 Verify @require_tenant decorator
    - _Requirements: 20.3_

- [ ] 14. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 9: Feature Flags and File Upload

- [ ] 15. Verify Feature Flag Patterns
  - [ ] 15.1 Review FlagStatus and RolloutStrategy enums
    - _Requirements: 18.1, 18.3_
  - [ ] 15.2 Review FlagEvaluation return type
    - _Requirements: 18.2_
  - [ ] 15.3 Write property test for percentage consistency
    - **Property 15: Feature Flag Percentage Consistency**
    - **Validates: Requirements 18.1, 18.2**

- [ ] 16. Verify File Upload Patterns
  - [ ] 16.1 Review StorageProvider[TMetadata] protocol
    - _Requirements: 19.1_
  - [ ] 16.2 Review validate_file Result return type
    - _Requirements: 19.2_
  - [ ] 16.3 Write property test for file validation checksum
    - **Property 16: File Validation Checksum**
    - **Validates: Requirements 19.2**

## Phase 10: Batch Operations and Read Models

- [ ] 17. Verify Batch Operation Patterns
  - [ ] 17.1 Review IBatchRepository interface
    - _Requirements: 22.1_
  - [ ] 17.2 Review BatchConfig and BatchErrorStrategy
    - _Requirements: 22.2_
  - [ ] 17.3 Write property test for batch chunking
    - **Property 17: Batch Operation Chunking**
    - **Validates: Requirements 22.1, 22.2**

- [ ] 18. Verify Read Model DTO Patterns
  - [ ] 18.1 Review frozen dataclass usage in read DTOs
    - Check UserReadDTO, UserListReadDTO, UserSearchResultDTO
    - _Requirements: 24.1_
  - [ ] 18.2 Review to_dict implementations
    - _Requirements: 24.2_
  - [ ] 18.3 Write property test for DTO immutability
    - **Property 18: Read DTO Immutability**
    - **Validates: Requirements 24.1**

- [ ] 19. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 11: Code Quality and Documentation

- [ ] 20. Code Quality Review
  - [ ] 20.1 Identify and refactor functions exceeding 50 lines
    - _Requirements: 15.1_
  - [ ] 20.2 Identify and split classes exceeding 300 lines
    - _Requirements: 15.2_
  - [ ] 20.3 Extract duplicated code (3+ occurrences) to shared utilities
    - _Requirements: 15.3_
  - [ ] 20.4 Replace magic numbers with named constants
    - _Requirements: 15.4_

- [ ] 21. Documentation Review
  - [ ] 21.1 Verify type parameter documentation in docstrings
    - _Requirements: 16.1_
  - [ ] 21.2 Add usage examples for complex generic methods
    - _Requirements: 16.3_
  - [ ] 21.3 Document Protocol contracts and expected behavior
    - _Requirements: 16.4_

- [ ] 22. Final Validation
  - [ ] 22.1 Run full test suite and verify all tests pass
  - [ ] 22.2 Run type checker (mypy/pyright) and fix any type errors
  - [ ] 22.3 Run linter (ruff) and fix any style issues
  - [ ] 22.4 Generate code review report with findings and improvements
