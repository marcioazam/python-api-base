# Implementation Plan

## Phase 1: Thread-Safe Singleton Patterns

- [x] 1. Implement thread-safe singletons

- [x] 1.1 Add thread-safe initialization to get_rbac_service()
  - Import threading module
  - Create module-level _rbac_lock = threading.Lock()
  - Implement double-check locking pattern
  - _Requirements: 1.1, 1.4, 1.5_

- [x] 1.2 Add thread-safe initialization to get_password_validator()
  - Create module-level _password_lock = threading.Lock()
  - Implement double-check locking pattern
  - _Requirements: 1.2, 1.4, 1.5_

- [x] 1.3 Add thread-safe initialization to get_audit_logger()
  - Create module-level _audit_lock = threading.Lock()
  - Implement double-check locking pattern
  - _Requirements: 1.3, 1.4, 1.5_

- [x] 1.4 Write property test for thread-safe singleton access
  - **Property 1: Thread-Safe Singleton Access**
  - **Validates: Requirements 1.1, 1.2, 1.3**

## Phase 2: JWT Refresh Token Memory Management

- [x] 2. Implement bounded token tracking

- [x] 2.1 Change _used_refresh_tokens from set to OrderedDict
  - Import OrderedDict from collections
  - Store (jti, expiry_datetime) pairs
  - _Requirements: 2.1, 2.2_

- [x] 2.2 Add max_tracked_tokens parameter to JWTService
  - Add DEFAULT_MAX_TRACKED_TOKENS = 10000 constant
  - Add max_tracked_tokens parameter to __init__
  - _Requirements: 2.5_

- [x] 2.3 Implement _cleanup_expired_tokens() method
  - Iterate through tokens and remove expired ones
  - Call before checking replay protection
  - _Requirements: 2.3, 2.4_

- [x] 2.4 Implement FIFO removal when limit is reached
  - Use popitem(last=False) to remove oldest
  - Apply after adding new token
  - _Requirements: 2.2_

- [x] 2.5 Write property test for bounded token tracking
  - **Property 2: Bounded Token Tracking Memory**
  - **Validates: Requirements 2.1, 2.2**

- [x] 2.6 Write property test for FIFO removal
  - **Property 3: Token Tracking FIFO Removal**
  - **Validates: Requirements 2.2**

- [x] 3. Checkpoint - Make sure all tests are passing
  - Ensure all tests pass, ask the user if questions arise.

## Phase 3: JWT Validator Fail-Closed Behavior

- [x] 4. Implement fail-closed revocation check

- [x] 4.1 Update validate_with_revocation() with try/except
  - Wrap revocation store call in try/except
  - Re-raise InvalidTokenError without modification
  - Catch all other exceptions and fail closed
  - _Requirements: 3.1, 3.5_

- [x] 4.2 Add error logging for revocation store failures
  - Log error with jti and exception details
  - Use logger.error() with extra context
  - _Requirements: 3.2_

- [x] 4.3 Raise InvalidTokenError with appropriate message
  - Message: "Unable to verify token status"
  - Chain original exception with "from e"
  - _Requirements: 3.3_

- [x] 4.4 Write property test for fail-closed behavior
  - **Property 4: Fail-Closed Revocation Check**
  - **Validates: Requirements 3.1, 3.3, 3.5**

## Phase 4: Audit Logger Correlation ID Support

- [x] 5. Add correlation ID support to audit logger

- [x] 5.1 Add correlation_id field to SecurityEvent dataclass
  - Make it a required field after timestamp
  - Update to_dict() to include correlation_id
  - _Requirements: 4.5_

- [x] 5.2 Add correlation_id_provider parameter to SecurityAuditLogger
  - Accept Callable[[], str] | None
  - Default to generate_ulid if not provided
  - _Requirements: 4.1, 4.3_

- [x] 5.3 Update _create_event() to use correlation_id_provider
  - Call provider to get correlation_id
  - Pass to SecurityEvent constructor
  - _Requirements: 4.2, 4.4_

- [x] 5.4 Write property test for correlation ID in events
  - **Property 5: Correlation ID in All Events**
  - **Validates: Requirements 4.2, 4.3, 4.5**

- [x] 5.5 Write property test for custom correlation ID provider
  - **Property 6: Custom Correlation ID Provider**
  - **Validates: Requirements 4.4**

- [x] 6. Checkpoint - Make sure all tests are passing
  - Ensure all tests pass, ask the user if questions arise.

## Phase 5: Enhanced PII Redaction Patterns

- [x] 7. Expand PII redaction patterns

- [x] 7.1 Add Bearer token redaction pattern
  - Pattern: Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+
  - Replacement: "Bearer [REDACTED]"
  - _Requirements: 5.2_

- [x] 7.2 Add credit card pattern with separators
  - Pattern: (?:\d{4}[-\s]?){3}\d{4}
  - Replacement: "[CARD]"
  - _Requirements: 5.3_

- [x] 7.3 Add international phone number pattern
  - Pattern: \+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}
  - Replacement: "[PHONE]"
  - _Requirements: 5.4_

- [x] 7.4 Add configurable IP address redaction
  - Add redact_ip_addresses parameter to __init__
  - Add IPv4 and IPv6 patterns to separate list
  - Apply only when enabled
  - _Requirements: 5.1, 5.5_

- [x] 7.5 Write property test for Bearer token redaction
  - **Property 7: Bearer Token Redaction**
  - **Validates: Requirements 5.2**

- [x] 7.6 Write property test for credit card redaction
  - **Property 8: Credit Card Redaction with Separators**
  - **Validates: Requirements 5.3**

- [x] 7.7 Write property test for IP address redaction
  - **Property 9: IP Address Redaction**
  - **Validates: Requirements 5.1, 5.5**

## Phase 6: Module Public API Exports

- [x] 8. Add __all__ exports to modules

- [x] 8.1 Add __all__ to exceptions.py
  - List all public exception classes
  - Include ErrorContext
  - _Requirements: 6.1_

- [x] 8.2 Update __all__ in config.py
  - Add redact_url_credentials to exports
  - Ensure all Settings classes are listed
  - _Requirements: 6.2_

- [x] 8.3 Add __all__ to container.py
  - List Container, LifecycleManager, LifecycleHookError
  - Include create_container and lifecycle
  - _Requirements: 6.3_

- [x] 8.4 Write test for module __all__ completeness
  - **Property 10: Module __all__ Completeness**
  - **Validates: Requirements 6.1, 6.2, 6.3**

## Phase 7: Container Redis URL Configuration

- [x] 9. Fix Redis URL configuration in container

- [x] 9.1 Update redis_cache provider to use RedisSettings
  - Access cfg.redis.url instead of deriving from database
  - Check cfg.redis.enabled before using Redis
  - _Requirements: 7.1, 7.3, 7.4_

- [x] 9.2 Add fallback for missing Redis configuration
  - Default to "redis://localhost:6379" if not configured
  - _Requirements: 7.2_

## Phase 8: Code Quality Constants

- [x] 10. Replace magic numbers with named constants

- [x] 10.1 Add password scoring constants to password_policy.py
  - SCORE_PER_REQUIREMENT: Final[int] = 20
  - MAX_SCORE: Final[int] = 100
  - LENGTH_BONUS_MULTIPLIER: Final[int] = 2
  - MAX_LENGTH_BONUS: Final[int] = 20
  - COMMON_PASSWORD_PENALTY: Final[int] = 40
  - _Requirements: 8.1, 8.2, 8.4, 8.5_

- [x] 10.2 Add Final type hint to RATE_LIMIT_PATTERN in config.py
  - Import Final from typing
  - Apply to regex pattern constant
  - _Requirements: 8.3_

- [x] 11. Final Checkpoint - Make sure all tests are passing
  - Ensure all tests pass, ask the user if questions arise.
