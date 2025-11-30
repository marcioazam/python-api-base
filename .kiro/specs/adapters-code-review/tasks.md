# Implementation Plan

- [x] 1. Fix SQLModelRepository boolean comparison and add validation
  - [x] 1.1 Replace `== False` with SQLAlchemy `is_(false())` syntax in get_by_id and get_all methods
    - Import `false` from sqlalchemy
    - Update soft delete filter to use `.is_(false())`
    - _Requirements: 1.2_
  - [x] 1.2 Add input validation in create method
    - Validate entity_data before model_validate
    - Add proper error handling for validation failures
    - _Requirements: 1.3_
  - [x] 1.3 Write property test for repository data integrity
    - **Property 1: Repository Data Integrity**
    - **Validates: Requirements 1.1, 1.3**
  - [x] 1.4 Write property test for pagination correctness
    - **Property 15: Repository Pagination Correctness**
    - **Validates: Requirements 9.4**

- [x] 2. Enhance rate limiter IP validation
  - [x] 2.1 Add length check and stricter validation to _is_valid_ip function
    - Add max length check (45 chars for IPv6)
    - Add empty string check
    - Improve logging for invalid IPs
    - _Requirements: 2.2_
  - [x] 2.2 Write property test for IP validation
    - **Property 3: IP Validation Correctness**
    - **Validates: Requirements 2.2**

- [x] 3. Add Request ID validation in middleware
  - [x] 3.1 Add UUID format validation to RequestIDMiddleware
    - Create UUID_PATTERN regex constant
    - Add _is_valid_request_id helper function
    - Generate new UUID if incoming header is invalid
    - _Requirements: 2.5_
  - [x] 3.2 Write property test for request ID validation
    - **Property 6: Request ID Format Validation**
    - **Validates: Requirements 2.5**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Improve security headers middleware
  - [x] 5.1 Verify all OWASP-recommended headers are included
    - X-Frame-Options, X-Content-Type-Options, X-XSS-Protection present ✓
    - Strict-Transport-Security, Referrer-Policy present ✓
    - CSP is configurable via constructor parameter ✓
    - _Requirements: 2.1_
  - [x] 5.2 Write property test for security headers completeness
    - **Property 2: Security Headers Completeness**
    - **Validates: Requirements 2.1**

- [x] 6. Enhance request logger sensitive data masking
  - [x] 6.1 Review and expand SENSITIVE_FIELDS and SENSITIVE_HEADERS sets
    - Comprehensive SENSITIVE_FIELDS set with 18 patterns ✓
    - SENSITIVE_HEADERS includes authorization, api-key, token, cookie ✓
    - Case-insensitive matching via key_lower ✓
    - _Requirements: 2.3_
  - [x] 6.2 Write property test for sensitive data masking
    - **Property 4: Sensitive Data Masking**
    - **Validates: Requirements 2.3**

- [x] 7. Improve error handler RFC 7807 compliance
  - [x] 7.1 Ensure all error responses follow RFC 7807 format
    - ProblemDetail model has all required fields (type, title, status, detail, instance, errors) ✓
    - unhandled_exception_handler returns generic error without internal details ✓
    - _Requirements: 2.4_
  - [x] 7.2 Write property test for error response compliance
    - **Property 5: Error Response RFC 7807 Compliance**
    - **Validates: Requirements 2.4**

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Fix API versioning module
  - [x] 9.1 Improve version extraction with strict validation
    - Add regex pattern for version format validation
    - Return None for invalid version formats
    - _Requirements: 3.2_
  - [x] 9.2 Ensure deprecation headers follow RFC 8594
    - Deprecation header set to "true" ✓
    - Sunset header uses HTTP-date format (strftime) ✓
    - _Requirements: 3.1, 3.4_
  - [x] 9.3 Write property test for version extraction safety
    - **Property 8: Version Extraction Safety**
    - **Validates: Requirements 3.2**
  - [x] 9.4 Write property test for deprecation headers compliance
    - **Property 7: Deprecation Headers RFC 8594 Compliance**
    - **Validates: Requirements 3.1, 3.4**

- [x] 10. Improve GraphQL cursor handling
  - [x] 10.1 Add robust error handling to decode_cursor function
    - Handle empty cursor input
    - Catch all exceptions and raise generic ValueError
    - Remove internal details from error messages
    - _Requirements: 4.1_
  - [x] 10.2 Verify pagination boundary calculations in connection_from_list
    - has_previous_page and has_next_page correctly calculated ✓
    - Edge cases handled (empty list returns empty edges) ✓
    - _Requirements: 4.2_
  - [x] 10.3 Write property test for cursor round trip
    - **Property 9: Cursor Encoding Round Trip**
    - **Validates: Requirements 4.1**
  - [x] 10.4 Write property test for pagination boundaries
    - **Property 10: Pagination Boundary Correctness**
    - **Validates: Requirements 4.2**

- [x] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Enhance WebSocket ConnectionManager
  - [x] 12.1 Add client_id uniqueness validation in connect method
    - Check if client_id already exists
    - Disconnect existing connection or reject new one
    - _Requirements: 5.1_
  - [x] 12.2 Improve broadcast fault tolerance
    - Exceptions caught per connection with try/except ✓
    - Continues broadcasting to other connections on failure ✓
    - Returns count of successful deliveries ✓
    - _Requirements: 5.2_
  - [x] 12.3 Ensure room cleanup in disconnect method
    - Currently removes client from rooms but doesn't delete empty rooms
    - Add empty room cleanup in disconnect method
    - _Requirements: 5.3_
  - [x] 12.4 Ensure atomic disconnect from all rooms
    - Client removed from all rooms in disconnect method ✓
    - Uses discard to avoid errors ✓
    - _Requirements: 5.5_
  - [x] 12.5 Write property test for connection uniqueness
    - **Property 11: WebSocket Connection Uniqueness**
    - **Validates: Requirements 5.1**
  - [x] 12.6 Write property test for broadcast fault tolerance
    - **Property 12: Broadcast Fault Tolerance**
    - **Validates: Requirements 5.2**
  - [x] 12.7 Write property test for room cleanup invariant
    - **Property 13: Room Cleanup Invariant**
    - **Validates: Requirements 5.3**
  - [x] 12.8 Write property test for disconnect atomicity
    - **Property 14: Disconnect Atomicity**
    - **Validates: Requirements 5.5**

- [x] 13. Fix auth constants security issue
  - [x] 13.1 Add production warning for demo users
    - Import settings and check debug mode
    - Log warning if demo users used in production
    - Consider moving to environment variables
    - _Requirements: 6.3_

- [x] 14. Improve module organization and documentation
  - [x] 14.1 Add __all__ exports to adapter __init__.py files
    - Add __all__ to src/my_api/adapters/__init__.py
    - Add __all__ to src/my_api/adapters/api/__init__.py
    - Add __all__ to src/my_api/adapters/api/middleware/__init__.py
    - Add __all__ to src/my_api/adapters/repositories/__init__.py
    - _Requirements: 7.1_
  - [x] 14.2 Add missing docstrings to public functions
    - Ensure Args, Returns, Raises sections are complete
    - Follow Google docstring style
    - _Requirements: 7.2_

- [x] 15. Final Checkpoint - Ensure all tests pass

  - Ensure all tests pass, ask the user if questions arise.
