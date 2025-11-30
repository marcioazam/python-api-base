# Implementation Plan

## Phase 1: Critical Security Fixes

- [x] 1. Implement secrets_manager providers
  - [x] 1.1 Create BaseSecretsProvider abstract class
    - Define abstract methods: get_secret, create_secret, update_secret, delete_secret, rotate_secret
    - Use ABC and abstractmethod decorators
    - Add proper type hints and docstrings
    - _Requirements: 1.1_
  - [x] 1.2 Implement LocalSecretsProvider
    - Create in-memory storage using dict
    - Implement all abstract methods
    - Raise SecretNotFoundError for missing secrets
    - Return SecretMetadata with UTC timestamps
    - _Requirements: 1.2, 1.3, 1.4, 1.5_
  - [x] 1.3 Write property test for Secret CRUD Round-Trip
    - **Property 1: Secret CRUD Round-Trip Consistency**
    - **Validates: Requirements 1.3, 1.4, 1.5**
  - [x] 1.4 Write property test for Secret Not Found Error
    - **Property 2: Secret Not Found Error**
    - **Validates: Requirements 1.3**

- [x] 2. Add logging to secrets rotation

  - [x] 2.1 Add module-level logger to manager.py
    - Import logging module
    - Create _logger = logging.getLogger(__name__)
    - _Requirements: 2.3_
  - [x] 2.2 Add success logging in rotation_loop
    - Log info message after successful rotation
    - Include secret_name in extra dict
    - _Requirements: 2.1_
  - [x] 2.3 Add exception logging in rotation_loop
    - Replace bare except with _logger.exception()
    - Include secret_name in extra dict
    - _Requirements: 2.2_
  - [x] 2.4 Write unit tests for rotation logging
    - Test success logging with mock logger
    - Test failure logging with mock logger
    - _Requirements: 2.1, 2.2_

- [x] 3. Checkpoint - Ensure critical fixes pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 2: Security Enhancements

- [x] 4. Add secret key length validation
  - [x] 4.1 Add MIN_SECRET_KEY_LENGTH constant
    - Define constant = 32 (256 bits)
    - Add to service.py
    - _Requirements: 6.1, 6.2_
  - [x] 4.2 Add validation in RequestSigner.__init__
    - Check key length after encoding
    - Raise ValueError with descriptive message
    - _Requirements: 6.1, 6.3_
  - [x] 4.3 Add validation in RequestVerifier.__init__
    - Check key length after encoding
    - Raise ValueError with descriptive message
    - _Requirements: 6.2, 6.3_
  - [x] 4.4 Write property test for key length validation
    - **Property 4: Secret Key Minimum Length Validation**
    - **Validates: Requirements 6.1, 6.2, 6.3**

- [x] 5. Fix ReDoS vulnerability in WAF patterns
  - [x] 5.1 Update SQL_INJECTION_PATTERNS with bounded quantifiers
    - Replace .* with .{0,100}
    - Test patterns still detect attacks
    - _Requirements: 5.1, 5.2_
  - [x] 5.2 Add graceful error handling for regex compilation
    - Wrap re.compile in try/except in WAFRule.__post_init__
    - Log warning for invalid patterns
    - _Requirements: 5.3_
  - [x] 5.3 Write property test for ReDoS protection
    - **Property 5: ReDoS Protection - Bounded Pattern Matching**
    - **Validates: Requirements 5.1**

- [x] 6. Checkpoint - Ensure security fixes pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 3: Code Quality Improvements

- [x] 7. Fix timezone awareness in WAF models
  - [x] 7.1 Update ThreatDetection timestamp default
    - Import timezone from datetime
    - Change default_factory to use timezone.utc
    - _Requirements: 4.1, 4.2_
  - [x] 7.2 Write property test for timezone preservation
    - **Property 3: Timezone Preservation**
    - **Validates: Requirements 4.1, 4.3**

- [x] 8. Cleanup imports in request_signing
  - [x] 8.1 Clean request_signing/enums.py
    - Remove unused imports (hashlib, hmac, time, dataclass, datetime, Any)
    - Keep only Enum import
    - _Requirements: 3.1_
  - [x] 8.2 Clean request_signing/config.py
    - Remove unused imports
    - Keep only necessary imports for SignatureConfig
    - _Requirements: 3.2_
  - [x] 8.3 Move secrets import to top of service.py
    - Add import secrets at top of file
    - Remove import from inside sign() method
    - _Requirements: 7.1, 7.2_

- [x] 9. Cleanup imports in response_transformation
  - [x] 9.1 Clean response_transformation/enums.py
    - Remove unused imports (ABC, abstractmethod, dataclass, field, datetime, Any, Callable, Generic, TypeVar)
    - Keep only Enum import
    - _Requirements: 3.3_

- [x] 10. Cleanup imports in streaming
  - [x] 10.1 Clean streaming/enums.py
    - Remove unused imports
    - Keep only Enum import
    - _Requirements: 3.4_
  - [x] 10.2 Clean streaming/config.py
    - Remove unused imports
    - Keep only necessary imports
    - _Requirements: 3.4_
  - [x] 10.3 Clean streaming/models.py
    - Remove unused imports
    - Keep only necessary imports
    - _Requirements: 3.4_

- [x] 11. Expand utils module exports
  - [x] 11.1 Update utils/__init__.py with all exports
    - Import functions from datetime, ids, pagination, password, sanitization
    - Update __all__ list with all public functions
    - _Requirements: 8.1, 8.2_
  - [x] 11.2 Write property test for utils exports
    - **Property 6: Utils Module Exports Completeness**
    - **Validates: Requirements 8.1**

- [x] 12. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
