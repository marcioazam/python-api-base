# Implementation Plan

## Phase 1: Configuration Security Hardening

- [ ] 1. Enhance Settings validation and security
- [ ] 1.1 Add secret key entropy validation with field_validator
  - Implement validator to check minimum 32 characters (256 bits)
  - Raise ValueError with clear message for insufficient entropy
  - _Requirements: 1.1_

- [ ] 1.2 Write property test for secret key entropy validation
  - **Property 1: Secret Key Entropy Validation**
  - **Validates: Requirements 1.1**

- [ ] 1.3 Add CORS wildcard warning for production
  - Implement field_validator for cors_origins
  - Log security warning when "*" is present and ENVIRONMENT=production
  - _Requirements: 1.2_

- [ ] 1.4 Implement database URL credential redaction
  - Create utility function to redact credentials from URLs
  - Apply redaction in __repr__ and logging contexts
  - _Requirements: 1.3_

- [ ] 1.5 Write property test for database URL credential redaction
  - **Property 2: Database URL Credential Redaction**
  - **Validates: Requirements 1.3**

- [ ] 1.6 Add rate limit configuration validation
  - Implement validator for rate_limit field format (e.g., "100/minute")
  - Raise ValidationError with specific details for invalid formats
  - _Requirements: 1.4_

- [ ] 1.7 Write property test for rate limit validation
  - Test various valid and invalid rate limit formats
  - **Validates: Requirements 1.4**

## Phase 2: Exception Hierarchy Improvements

- [ ] 2. Enhance exception hierarchy with tracing support
- [ ] 2.1 Create ErrorContext dataclass
  - Add correlation_id, timestamp, request_path fields
  - Make it frozen/immutable
  - _Requirements: 2.1_

- [ ] 2.2 Update AppException with ErrorContext
  - Add context parameter to __init__
  - Auto-generate correlation_id and timestamp if not provided
  - Update to_dict() to include new fields
  - _Requirements: 2.1, 2.2_

- [ ] 2.3 Write property test for exception serialization consistency
  - **Property 3: Exception Serialization Consistency**
  - **Validates: Requirements 2.1, 2.2**

- [ ] 2.4 Update ValidationError to support both list and dict formats
  - Modify constructor to accept Union[list, dict] for errors
  - Normalize to consistent internal format
  - _Requirements: 2.3_

- [ ] 2.5 Write property test for ValidationError format handling
  - Test both list and dict error formats
  - **Validates: Requirements 2.3**

- [ ] 2.6 Ensure exception chaining preserves stack traces
  - Review all exception raises to use "from e" syntax
  - Add __cause__ preservation in to_dict()
  - _Requirements: 2.4_

## Phase 3: Dependency Injection Container Refactoring

- [ ] 3. Improve DI container and lifecycle management
- [ ] 3.1 Add dependency validation on container initialization
  - Implement validate_dependencies() method
  - Check all required providers are configured
  - _Requirements: 3.1_

- [ ] 3.2 Improve lifecycle hook execution order guarantees
  - Document and enforce registration order execution
  - Add hook priority support (optional)
  - _Requirements: 3.4_

- [ ] 3.3 Write property test for lifecycle hook execution order
  - **Property 4: Lifecycle Hook Execution Order**
  - **Validates: Requirements 3.4**

- [ ] 3.4 Implement error aggregation for shutdown hooks
  - Continue executing all hooks even if some fail
  - Collect and log all errors
  - Raise aggregated exception at end if any failed
  - _Requirements: 3.5_

- [ ] 3.5 Write property test for shutdown hook error aggregation
  - **Property 5: Lifecycle Hook Error Aggregation**
  - **Validates: Requirements 3.5**

- [ ] 3.6 Add hook inspection and clearing for testability
  - Implement get_hooks() method
  - Implement clear_hooks() method
  - _Requirements: 11.5_

- [ ] 4. Checkpoint - Make sure all tests are passing
  - Ensure all tests pass, ask the user if questions arise.

## Phase 4: JWT Service Security Enhancement

- [ ] 5. Enhance JWT service with security improvements
- [ ] 5.1 Add injectable TimeSource protocol
  - Create TimeSource Protocol
  - Implement SystemTimeSource default
  - Update JWTService to use TimeSource
  - _Requirements: 11.1_

- [ ] 5.2 Add configurable clock skew tolerance
  - Add clock_skew_seconds parameter to JWTService
  - Apply skew in expiration checks
  - _Requirements: 4.4_

- [ ] 5.3 Write property test for JWT required claims
  - **Property 6: JWT Required Claims**
  - **Validates: Requirements 4.1**

- [ ] 5.4 Implement refresh token replay protection
  - Track used refresh token JTIs
  - Reject reused refresh tokens
  - _Requirements: 4.5_

- [ ] 5.5 Write property test forr refresh token replay protection
  - **Validates: Requirements 4.5**

## Phase 5: JWT Validator Algorithm Restriction

- [ ] 6. Harden JWT validator algorithm handling
- [ ] 6.1 Strengthen algorithm validation
  - Validate algorithm before any decoding
  - Check header algorithm matches expected
  - _Requirements: 4.2, 5.4_

- [ ]* 6.2 Write property test for JWT algorithm validation
  - **Property 7: JWT Algorithm Validation**
  - **Validates: Requirements 4.2, 5.1, 5.4**

- [ ] 6.3 Add explicit "none" algorithm rejection
  - Check for "none" algorithm in header
  - Log warning and reject immediately
  - _Requirements: 4.3_

- [ ]* 6.4 Write property test for none algorithm rejection
  - **Property 8: JWT None Algorithm Rejection**
  - **Validates: Requirements 4.3, 5.5**

- [ ] 6.5 Add production mode secure algorithm enforcement
  - Add require_secure_algorithm parameter
  - Reject HS256 when enabled
  - _Requirements: 5.2_

- [ ]* 6.6 Write property test for secure algorithm enforcement
  - **Validates: Requirements 5.2**

## Phase 6: Token Revocation Support

- [ ] 7. Implement token revocation functionality
- [ ] 7.1 Implement fail-closed behavior for revocation store
  - Catch revocation store exceptions
  - Reject token if store is unavailable
  - Log error with details
  - _Requirements: 6.5_

- [ ]* 7.2 Write property test for revocation fail-closed
  - **Property 10: Revocation Store Fail-Closed**
  - **Validates: Requirements 6.5**

- [ ]* 7.3 Write property test for token revocation round-trip
  - **Property 9: Token Revocation Round-Trip**
  - **Validates: Requirements 6.1, 6.2**

- [ ] 8. Checkpoint - Make sure all tests are passing
  - Ensure all tests pass, ask the user if questions arise.

## Phase 7: Password Policy Validation

- [ ] 9. Enhance password policy validation
- [ ] 9.1 Review and verify password complexity validation
  - Ensure all complexity rules are properly checked
  - Verify error messages are specific
  - _Requirements: 7.1_

- [ ]* 9.2 Write property test for password complexity validation
  - **Property 11: Password Complexity Validation**
  - **Validates: Requirements 7.1**

- [ ]* 9.3 Write property test for common password rejection
  - **Property 12: Common Password Rejection**
  - **Validates: Requirements 7.2**

- [ ]* 9.4 Write property test for password strength score bounds
  - **Property 13: Password Strength Score Bounds**
  - **Validates: Requirements 7.3**

- [ ]* 9.5 Write property test for Argon2id hash format
  - **Property 14: Argon2id Hash Format**
  - **Validates: Requirements 7.5**

## Phase 8: RBAC Service Improvements

- [ ] 10. Enhance RBAC service functionality
- [ ] 10.1 Add permission caching with TTL
  - Implement permission cache with configurable TTL
  - Add cache invalidation on role changes
  - _Requirements: 8.4_

- [ ] 10.2 Add audit logging for role changes
  - Inject SecurityAuditLogger
  - Log role additions, updates, and deletions
  - _Requirements: 8.2_

- [ ]* 10.3 Write property test for RBAC permission inheritance
  - **Property 15: RBAC Permission Inheritance**
  - **Validates: Requirements 8.1**

- [ ]* 10.4 Write property test for RBAC ANY/ALL semantics
  - **Property 16: RBAC ANY/ALL Semantics**
  - **Validates: Requirements 8.3**

- [ ] 10.5 Fix require_permission decorator for sync/async
  - Ensure decorator works with both function types
  - Add proper type hints
  - _Requirements: 8.5_

- [ ]* 10.6 Write property test for decorator compatibility
  - **Property 17: RBAC Decorator Compatibility**
  - **Validates: Requirements 8.5**

## Phase 9: Security Audit Logger Enhancement

- [ ] 11. Enhance security audit logger
- [ ] 11.1 Add correlation_id support
  - Add correlation_id_provider parameter
  - Include correlation_id in all events
  - _Requirements: 9.1_

- [ ]* 11.2 Write property test for audit log required fields
  - **Property 18: Audit Log Required Fields**
  - **Validates: Requirements 9.1**

- [ ] 11.3 Expand PII redaction patterns
  - Add Bearer token pattern
  - Add more phone number formats
  - Add credit card with separators
  - _Requirements: 9.2_

- [ ]* 11.4 Write property test for PII redaction completeness
  - **Property 19: PII Redaction Completeness**
  - **Validates: Requirements 9.2**

- [ ]* 11.5 Write property test for secret access logging safety
  - **Property 20: Secret Access Logging Safety**
  - **Validates: Requirements 9.5**

- [ ] 12. Checkpoint - Make sure all tests are passing
  - Ensure all tests pass, ask the user if questions arise.

## Phase 10: Code Quality and Testability

- [ ] 13. Improve code quality and testability
- [ ] 13.1 Ensure thread-safe singleton patterns
  - Review get_settings(), get_rbac_service(), get_audit_logger()
  - Add thread-safe initialization if needed
  - _Requirements: 10.4_

- [ ]* 13.2 Write property test for thread-safe singleton access
  - **Property 21: Thread-Safe Singleton Access**
  - **Validates: Requirements 10.4**

- [ ]* 13.3 Write property test for environment variable override
  - **Property 22: Environment Variable Override**
  - **Validates: Requirements 11.2**

## Phase 11: Token Pretty Printing

- [ ] 14. Enhance token debugging capabilities
- [ ] 14.1 Improve TokenPayload pretty_print method
  - Ensure all fields are included
  - Format timestamps in ISO 8601
  - Add optional redaction for sensitive claims
  - _Requirements: 12.1, 12.4, 12.5_

- [ ]* 14.2 Write property test for token pretty print completeness
  - **Property 23: Token Pretty Print Completeness**
  - **Validates: Requirements 12.1**

- [ ]* 14.3 Write property test for token serialization round-trip
  - **Property 24: Token Serialization Round-Trip**
  - **Validates: Requirements 12.2**

- [ ]* 14.4 Write property test for ISO 8601 timestamp format
  - **Property 25: ISO 8601 Timestamp Format**
  - **Validates: Requirements 12.4**

- [ ] 15. Final Checkpoint - Make sure all tests are passing
  - Ensure all tests pass, ask the user if questions arise.
