# Implementation Plan

## Phase 1: Event Sourcing Refactoring (522 lines)

- [x] 1. Refactor event_sourcing.py into focused package
  - [x] 1.1 Create event_sourcing package structure
    - Create `src/my_api/shared/event_sourcing/` directory
    - Create empty `__init__.py` file
    - _Requirements: 1.1, 2.1_

  - [x] 1.2 Extract exceptions module
    - Move `ConcurrencyError` to `event_sourcing/exceptions.py`
    - _Requirements: 2.1_

  - [x] 1.3 Extract events module
    - Move `SourcedEvent`, `EventStream` to `event_sourcing/events.py`
    - _Requirements: 2.1_

  - [x] 1.4 Extract snapshots module
    - Move `Snapshot` to `event_sourcing/snapshots.py`
    - _Requirements: 2.4_

  - [x] 1.5 Extract aggregate module
    - Move `Aggregate`, `AggregateId` to `event_sourcing/aggregate.py`
    - _Requirements: 2.1_

  - [x] 1.6 Extract store module
    - Move `EventStore`, `InMemoryEventStore` to `event_sourcing/store.py`
    - _Requirements: 2.2_

  - [x] 1.7 Extract projections module
    - Move `Projection`, `InMemoryProjection` to `event_sourcing/projections.py`
    - _Requirements: 2.3_

  - [x] 1.8 Extract repository module
    - Move `EventSourcedRepository` to `event_sourcing/repository.py`
    - _Requirements: 2.1_

  - [x] 1.9 Create __init__.py with re-exports
    - Add all public symbols to `__all__`
    - Ensure backward compatibility
    - _Requirements: 1.2, 2.5_

  - [x] 1.10 Write property test for backward compatibility
    - **Property 1: Backward Compatibility After Refactoring**
    - **Validates: Requirements 1.2, 1.4**

  - [x] 1.11 Write property test for event sourcing round-trip
    - **Property 2: Event Sourcing Round-Trip**
    - **Validates: Requirements 2.5, 12.1**

- [x] 2. Checkpoint - Verify event_sourcing refactoring
  - Ensure all tests pass, ask the user if questions arise.

## Phase 2: Saga Refactoring (493 lines)

- [x] 3. Refactor saga.py into focused package
  - [x] 3.1 Create saga package structure
    - Create `src/my_api/shared/saga/` directory
    - _Requirements: 1.1, 3.1_

  - [x] 3.2 Extract enums module
    - Move `SagaStatus`, `StepStatus` to `saga/enums.py`
    - _Requirements: 3.1_

  - [x] 3.3 Extract context module
    - Move `SagaContext` to `saga/context.py`
    - _Requirements: 3.2_

  - [x] 3.4 Extract steps module
    - Move `SagaStep`, `StepResult` to `saga/steps.py`
    - _Requirements: 3.1_

  - [x] 3.5 Extract orchestrator module
    - Move `Saga`, `SagaResult` to `saga/orchestrator.py`
    - _Requirements: 3.3_

  - [x] 3.6 Extract builder module
    - Move `SagaBuilder` to `saga/builder.py`
    - _Requirements: 3.4_

  - [x] 3.7 Extract manager module
    - Move `SagaOrchestrator` to `saga/manager.py`
    - _Requirements: 3.1_

  - [x] 3.8 Create __init__.py with re-exports
    - Ensure backward compatibility
    - _Requirements: 1.2, 3.5_

  - [x] 3.9 Write property test for saga compensation
    - **Property 3: Saga Compensation Completeness**
    - **Validates: Requirements 3.5, 12.2**

- [x] 4. Checkpoint - Verify saga refactoring
  - Ensure all tests pass, ask the user if questions arise.

## Phase 3: OAuth2 Refactoring (454 lines)

- [x] 5. Refactor oauth2.py into focused package
  - [x] 5.1 Create oauth2 package structure
    - Create `src/my_api/shared/oauth2/` directory
    - Create `src/my_api/shared/oauth2/providers/` subdirectory
    - _Requirements: 1.1, 4.1_

  - [x] 5.2 Extract enums module
    - Move `OAuthProvider` to `oauth2/enums.py`
    - _Requirements: 4.1_

  - [x] 5.3 Extract models module
    - Move `OAuthConfig`, `OAuthUserInfo`, `OAuthTokenResponse`, `OAuthState` to `oauth2/models.py`
    - _Requirements: 4.4_

  - [x] 5.4 Extract exceptions module
    - Move all OAuth errors to `oauth2/exceptions.py`
    - _Requirements: 4.1_

  - [x] 5.5 Extract state_store module
    - Move `StateStore`, `InMemoryStateStore` to `oauth2/state_store.py`
    - _Requirements: 4.1_

  - [x] 5.6 Extract base provider module
    - Move `BaseOAuthProvider` to `oauth2/base.py`
    - _Requirements: 4.1_

  - [x] 5.7 Extract Google provider
    - Move `GoogleOAuthProvider` to `oauth2/providers/google.py`
    - _Requirements: 4.2_

  - [x] 5.8 Extract GitHub provider
    - Move `GitHubOAuthProvider` to `oauth2/providers/github.py`
    - _Requirements: 4.3_

  - [x] 5.9 Create __init__.py files with re-exports
    - Main package and providers subpackage
    - _Requirements: 1.2, 4.5_

  - [x] 5.10 Write property test for OAuth state expiration
    - **Property 12: OAuth State Expiration**
    - **Validates: Requirements 12.3**

- [x] 6. Checkpoint - Verify oauth2 refactoring
  - Ensure all tests pass, ask the user if questions arise.

## Phase 4: Security Hardening

- [x] 7. Implement JWT security enhancements
  - [x] 7.1 Create JWTValidator with algorithm restriction
    - Implement ALLOWED_ALGORITHMS = ["RS256", "ES256"]
    - Add token revocation support
    - _Requirements: 6.1, 6.2_

  - [x] 7.2 Implement token refresh rotation
    - Invalidate old refresh token on use
    - Generate new refresh token
    - _Requirements: 6.4_

  - [x] 7.3 Write property test for JWT algorithm restriction
    - **Property 4: JWT Algorithm Restriction**
    - **Validates: Requirements 6.1, 6.2**

  - [x] 7.4 Write property test for token tampering detection
    - **Property 5: Token Tampering Detection**
    - **Validates: Requirements 6.1, 12.5**

  - [x] 7.5 Write property test for refresh token rotation
    - **Property 6: Refresh Token Rotation**
    - **Validates: Requirements 6.4**

- [x] 8. Implement input validation enhancements
  - [x] 8.1 Create InputSanitizer class
    - Implement XSS pattern detection
    - Implement SQL injection pattern detection
    - _Requirements: 7.1, 7.2_

  - [x] 8.2 Enhance Pydantic validation
    - Add custom validators for common attack patterns
    - _Requirements: 7.1_

  - [x] 8.3 Write property test for input validation
    - **Property 7: Input Validation Completeness**
    - **Validates: Requirements 7.1, 7.5**

  - [x] 8.4 Write property test for input sanitization
    - **Property 13: Input Sanitization Effectiveness**
    - **Validates: Requirements 7.2, 12.6**

- [x] 9. Checkpoint - Verify security enhancements
  - Ensure all tests pass, ask the user if questions arise.

## Phase 5: Security Headers & Rate Limiting

- [x] 10. Implement security headers middleware
  - [x] 10.1 Create SecurityHeadersMiddleware
    - Implement CSP, HSTS, X-Frame-Options, X-Content-Type-Options
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 10.2 Implement secure cookie attributes
    - Add Secure, HttpOnly, SameSite=Strict
    - _Requirements: 8.5_

  - [x] 10.3 Write property test for security headers
    - **Property 8: Security Headers Presence**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4**

  - [x] 10.4 Write property test for cookie security
    - **Property 9: Cookie Security Attributes**
    - **Validates: Requirements 8.5**

- [x] 11. Enhance rate limiting
  - [x] 11.1 Fix Retry-After header accuracy
    - Calculate actual retry time based on window
    - _Requirements: 9.2_

  - [x] 11.2 Implement tiered rate limiting
    - Support different limits by user role
    - _Requirements: 9.3_

  - [x] 11.3 Write property test for IP validation
    - **Property 10: IP Validation Correctness**
    - **Validates: Requirements 9.1, 12.4**

  - [x] 11.4 Write property test for rate limit response
    - **Property 11: Rate Limit Response Format**
    - **Validates: Requirements 9.2**

- [x] 12. Checkpoint - Verify security headers and rate limiting
  - Ensure all tests pass, ask the user if questions arise.

## Phase 6: Audit Logging & Secrets Management

- [x] 13. Implement security audit logging
  - [x] 13.1 Create SecurityAuditLogger
    - Log auth success/failure events
    - Log authorization denials
    - Log rate limit exceeded events
    - _Requirements: 10.4, 10.5_

  - [x] 13.2 Implement log sanitization
    - Redact PII and sensitive data (implemented via PII_PATTERNS in SecurityAuditLogger)
    - _Requirements: 7.6_

  - [x] 13.3 Write property test for audit log completeness
    - **Property 14: Audit Log Completeness**
    - **Validates: Requirements 10.4**

- [x] 14. Enhance secrets management
  - [x] 14.1 Implement secure secret access
    - Use environment variables or secrets manager
    - _Requirements: 10.1_

  - [x] 14.2 Add secret access logging
    - Log access without exposing values (implemented via log_secret_access in SecurityAuditLogger)
    - _Requirements: 10.3_

  - [x] 14.3 Write property test for secret access logging
    - **Property 15: Secret Access Logging**
    - **Validates: Requirements 10.3**

- [x] 15. Checkpoint - Verify audit logging and secrets
  - Ensure all tests pass, ask the user if questions arise.

## Phase 7: Additional Large File Refactoring

- [x] 16. Refactor remaining large files (batch 1)
  - [x] 16.1 Refactor advanced_specification.py (471 lines)
    - Extract to `advanced_specification/` package
    - _Requirements: 5.1_

  - [x] 16.2 Refactor cloud_provider_filter.py (456 lines)
    - Extract to `cloud_provider_filter/` package
    - _Requirements: 5.2_

  - [x] 16.3 Refactor fuzzing.py (453 lines)
    - Extract to `fuzzing/` package
    - _Requirements: 5.3_

- [-] 17. Refactor remaining large files (batch 2)
  - [x] 17.1 Refactor contract_testing.py (440 lines)
    - Extract to `contract_testing/` package
    - _Requirements: 5.4_

  - [x] 17.2 Refactor caching.py (543 lines)


    - Extract to `caching/` package
    - _Requirements: 5.5_


  - [ ] 17.3 Refactor compression.py (534 lines)
    - Extract to `compression/` package
    - _Requirements: 5.6_

- [-] 18. Refactor remaining large files (batch 3)
  - [ ] 18.1 Refactor secrets_manager.py (581 lines)
    - Extract to `secrets_manager/` package
    - _Requirements: 5.7_

  - [ ] 18.2 Refactor tiered_rate_limiter.py (483 lines)
    - Extract to `tiered_rate_limiter/` package
    - _Requirements: 5.8_

  - [x] 18.3 Refactor metrics_dashboard.py (411 lines)
    - Extract to `metrics_dashboard/` package
    - _Requirements: 5.9_

  - [ ] 18.4 Refactor asyncapi.py (473 lines)
    - Extract to `asyncapi/` package
    - _Requirements: 5.10_

- [ ] 19. Checkpoint - Verify all refactoring complete
  - Ensure all tests pass, ask the user if questions arise.

## Phase 8: File Size Compliance Validation & Cleanup

- [x] 20. Validate file size compliance
  - [x] 20.1 Create file size validation script
    - Check all Python files are under 400 lines
    - _Requirements: 1.1, 1.3_

  - [x] 20.2 Add file size check to CI/CD
    - Fail build if any file exceeds limit
    - _Requirements: 1.1_

  - [x] 20.3 Write property test for file size compliance
    - **Property 16: File Size Compliance Post-Refactoring**
    - **Validates: Requirements 1.1, 1.3**

- [ ] 21. Remove legacy monolithic files
  - [ ] 21.1 Remove src/my_api/shared/event_sourcing.py (656 lines)
    - Package exists at event_sourcing/, remove legacy file
    - _Requirements: 1.1_

  - [ ] 21.2 Remove src/my_api/shared/saga.py (630 lines)
    - Package exists at saga/, remove legacy file
    - _Requirements: 1.1_

  - [ ] 21.3 Remove src/my_api/shared/advanced_specification.py (615 lines)
    - Package exists at advanced_specification/, remove legacy file
    - _Requirements: 1.1_

  - [ ] 21.4 Remove src/my_api/shared/oauth2.py (561 lines)
    - Package exists at oauth2/, remove legacy file
    - _Requirements: 1.1_

  - [ ] 21.5 Remove src/my_api/shared/cloud_provider_filter.py (529 lines)
    - Package exists at cloud_provider_filter/, remove legacy file
    - _Requirements: 1.1_

- [ ] 22. Final Checkpoint - Complete validation
  - Ensure all tests pass, ask the user if questions arise.
  - Verify file size check passes with no violations
