# Implementation Plan

## 1. Database Session Management Improvements

- [x] 1.1 Add input validation to DatabaseSession initialization
  - Add validation for empty/whitespace database_url
  - Add bounds checking for pool_size (>= 1) and max_overflow (>= 0)
  - Raise ValueError with descriptive messages
  - _Requirements: 1.1, 1.4_

- [x] 1.2 Write property tests for database session validation
  - **Property 1: Database URL Validation**
  - **Property 2: Connection Pool Bounds Validation**
  - **Validates: Requirements 1.1, 1.4**

- [x] 1.3 Improve exception handling in session context manager
  - Ensure rollback is called before re-raising
  - Preserve exception chain with `raise from`
  - Add structured logging for session errors
  - _Requirements: 1.2, 8.4_

- [x] 1.4 Write property test for exception propagation
  - **Property 3: Session Exception Propagation**
  - **Validates: Requirements 1.2**

## 2. Token Store Security Improvements

- [x] 2.1 Add input validation to token store operations
  - Validate jti is not empty/whitespace
  - Validate user_id is not empty/whitespace
  - Validate expires_at is in the future
  - Move json import to module level in RedisTokenStore
  - _Requirements: 2.1, 2.5_

- [x] 2.2 Write property test for token store validation
  - **Property 4: Token Store Input Validation**
  - **Validates: Requirements 2.1**

- [x] 2.3 Implement StoredToken dataclass validation
  - Add __post_init__ validation for required fields
  - Ensure immutability is preserved
  - _Requirements: 2.1_

- [x] 2.4 Write property test for token serialization round-trip
  - **Property 5: Token Serialization Round-Trip**
  - **Validates: Requirements 2.2**

- [x] 2.5 Fix InMemoryTokenStore eviction logic
  - Ensure oldest tokens are removed when exceeding max_entries
  - Maintain chronological order
  - Add thread-safe trimming
  - _Requirements: 2.3_

- [x] 2.6 Write property test for token eviction order
  - **Property 6: Token Store Eviction Order**
  - **Validates: Requirements 2.3**

- [x] 2.7 Improve revoke_all_for_user atomicity
  - Use proper locking for InMemoryTokenStore
  - Use Redis pipeline for RedisTokenStore
  - _Requirements: 2.4_

- [x] 2.8 Write property test for user token revocation
  - **Property 7: User Token Revocation Completeness**
  - **Validates: Requirements 2.4**

## 3. Checkpoint - Verify Token Store Tests Pass

- [x] 3. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## 4. Audit Logger Improvements

- [x] 4.1 Add validation to AuditEntry.from_dict
  - Validate required fields (id, timestamp, action, resource_type, result)
  - Handle missing optional fields gracefully
  - _Requirements: 3.1_

- [x] 4.2 Write property test for audit entry serialization
  - **Property 8: AuditEntry Serialization Round-Trip**
  - **Validates: Requirements 3.1**

- [x] 4.3 Enforce UTC timezone in AuditEntry
  - Add __post_init__ validation for timezone-aware timestamp
  - Ensure log_action always uses UTC
  - _Requirements: 3.2_

- [x] 4.4 Write property test for UTC timestamp invariant
  - **Property 9: AuditEntry UTC Timestamp Invariant**
  - **Validates: Requirements 3.2**

- [x] 4.5 Improve InMemoryAuditLogger trimming
  - Use thread-safe list operations
  - Ensure newest entries are preserved
  - _Requirements: 3.3_

- [x] 4.6 Write property test for audit log filter correctness
  - **Property 10: Audit Log Filter Correctness**
  - **Validates: Requirements 3.4**

## 5. Telemetry Provider Improvements

- [x] 5.1 Add thread safety to global telemetry state
  - Use threading.Lock for _telemetry global
  - Make initialization atomic
  - _Requirements: 4.2_

- [x] 5.2 Write property test for initialization idempotence
  - **Property 11: Telemetry Initialization Idempotence**
  - **Validates: Requirements 4.2**

- [x] 5.3 Refactor traced decorator to reduce duplication
  - Extract common span handling logic
  - Improve function type detection
  - _Requirements: 4.3_

- [x] 5.4 Write property test for traced decorator
  - **Property 12: Traced Decorator Function Type Detection**
  - **Validates: Requirements 4.3**

## 6. Checkpoint - Verify Telemetry Tests Pass

- [x] 6. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## 7. Logging Configuration Improvements

- [x] 7.1 Improve PII redaction completeness
  - Handle nested dicts and lists recursively
  - Handle edge cases (bytes, None, custom objects)
  - Make PII patterns configurable
  - _Requirements: 5.1, 5.2_

- [x] 7.2 Write property test for PII redaction
  - **Property 13: PII Redaction Completeness**
  - **Validates: Requirements 5.1, 5.2**

- [x] 7.3 Add log_level validation
  - Validate against allowed levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Raise ValueError for invalid levels
  - _Requirements: 8.3_

- [x] 7.4 Improve request_id context propagation
  - Ensure context is properly cleared after request
  - Add tests for context isolation
  - _Requirements: 5.5_

- [x] 7.5 Write property test for request_id propagation
  - **Property 14: Request ID Context Propagation**
  - **Validates: Requirements 5.5**

## 8. Tracing Middleware Improvements

- [x] 8.1 Improve path exclusion logic
  - Support glob patterns for excluded paths
  - Add prefix matching option
  - _Requirements: 6.1_

- [x] 8.2 Write property test for path exclusion
  - **Property 15: Tracing Path Exclusion**
  - **Validates: Requirements 6.1**

- [x] 8.3 Fix HTTP status to span status mapping
  - Ensure 5xx maps to ERROR
  - Ensure 4xx maps to OK
  - Add proper status descriptions
  - _Requirements: 6.4_

- [x] 8.4 Write property test for status mapping
  - **Property 16: HTTP Status to Span Status Mapping**
  - **Validates: Requirements 6.4**

- [x] 8.5 Ensure metrics labels completeness
  - Verify method, path, status_code are always present
  - Use consistent types for labels
  - _Requirements: 6.5_

- [x] 8.6 Write property test for metrics labels
  - **Property 17: Metrics Labels Completeness**
  - **Validates: Requirements 6.5**

## 9. Error Handling Consistency

- [x] 9.1 Standardize validation error handling
  - Use ValueError consistently for validation failures
  - Include descriptive messages with context
  - _Requirements: 8.1_

- [x] 9.2 Write property test for validation error consistency
  - **Property 18: Validation Error Type Consistency**
  - **Validates: Requirements 8.1**

- [x] 9.3 Improve exception chain preservation
  - Use `raise ... from ...` pattern consistently
  - Preserve original exception context
  - _Requirements: 8.4_

- [x] 9.4 Write property test for exception chain preservation
  - **Property 19: Exception Chain Preservation**
  - **Validates: Requirements 8.4**

## 10. Final Checkpoint - All Tests Pass

- [x] 10. Final Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## 11. Code Quality and Documentation

- [x] 11.1 Update type hints to modern Python 3.10+ syntax
  - Replace Optional[X] with X | None
  - Replace Union[X, Y] with X | Y
  - Replace List[X] with list[X]
  - _Requirements: 7.1_

- [x] 11.2 Add docstrings for public APIs
  - Document all public functions and classes
  - Include parameter descriptions and return types
  - Add usage examples where helpful
  - _Requirements: 7.5_

- [x] 11.3 Create infrastructure exception hierarchy
  - Define InfrastructureError base class
  - Create specific exception types (DatabaseError, TokenStoreError, etc.)
  - _Requirements: 8.2_

- [x] 11.4 Write unit tests for exception hierarchy
  - Test exception inheritance
  - Test exception messages
  - _Requirements: 8.2_
