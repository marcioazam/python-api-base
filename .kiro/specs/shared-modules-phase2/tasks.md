# Implementation Plan

- [x] 1. Create shared utilities and base infrastructure
  - [x] 1.1 Create custom exception hierarchy for phase 2
    - Create exceptions in `src/my_api/shared/exceptions.py`: `Phase2ModuleError`, `PoolInvariantViolation`, `SnapshotIntegrityError`, `FilterValidationError`, `FederationValidationError`
    - Add type hints and docstrings
    - _Requirements: 2.3, 6.2, 13.1, 15.3_

  - [x] 1.2 Write property test for exception hierarchy
    - Verify all exceptions inherit from `Phase2ModuleError`
    - Verify error messages contain required context

- [x] 2. Refactor connection_pool module
  - [x] 2.1 Fix counter consistency in state transitions
    - Implement atomic `_transition_state()` method with lock
    - Ensure exactly one source counter decremented and one destination incremented
    - Add invariant validation after each transition
    - _Requirements: 2.1, 2.2_

  - [x] 2.2 Write property test for pool counter invariant
    - **Property 1: Pool Counter Invariant**
    - **Validates: Requirements 2.3**

  - [x] 2.3 Write property test for state transition counter consistency
    - **Property 4: State Transition Counter Consistency**
    - **Validates: Requirements 2.2**

  - [x] 2.4 Fix connection lifetime enforcement
    - Ensure connections exceeding max_lifetime are removed in health check
    - Add proper destruction awaiting
    - _Requirements: 1.1_

  - [x] 2.5 Write property test for connection lifetime enforcement
    - **Property 2: Connection Lifetime Enforcement**
    - **Validates: Requirements 1.1**

  - [x] 2.6 Fix pool closure completeness
    - Await all pending destructions before returning from close()
    - Handle destruction errors gracefully
    - _Requirements: 1.2_

  - [x] 2.7 Write property test for pool closure completeness
    - **Property 3: Pool Closure Completeness**
    - **Validates: Requirements 1.2**

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Refactor csp_generator module
  - [x] 4.1 Verify nonce security implementation
    - Ensure `secrets.token_urlsafe()` is used with minimum 16 bytes
    - Add nonce format validation
    - _Requirements: 3.1, 3.3_

  - [x] 4.2 Write property test for nonce entropy
    - **Property 6: Nonce Entropy**
    - **Validates: Requirements 3.1**

  - [x] 4.3 Write property test for nonce uniqueness
    - **Property 5: Nonce Uniqueness**
    - **Validates: Requirements 3.2**

  - [x] 4.4 Add CSP header determinism
    - Sort directives consistently in `to_header_value()`
    - Ensure same policy produces identical headers
    - _Requirements: 4.3_

  - [x] 4.5 Write property test for CSP header determinism
    - **Property 7: CSP Header Determinism**
    - **Validates: Requirements 4.3**

- [x] 5. Refactor event_sourcing module
  - [x] 5.1 Enhance ConcurrencyError with version info
    - Include expected and actual versions in error message
    - Add structured error attributes
    - _Requirements: 5.2_

  - [x] 5.2 Write property test for ConcurrencyError message content
    - **Property 9: ConcurrencyError Message Content**
    - **Validates: Requirements 5.2**

  - [x] 5.3 Add snapshot hash integrity
    - Add `state_hash` field to Snapshot
    - Compute SHA-256 of serialized state
    - _Requirements: 6.1_

  - [x] 5.4 Write property test for snapshot hash integrity
    - **Property 10: Snapshot Hash Integrity**
    - **Validates: Requirements 6.1**

  - [x] 5.5 Implement snapshot validation with fallback
    - Validate hash on load
    - Fall back to event replay on validation failure
    - Log warning on fallback
    - _Requirements: 6.2, 6.3_

  - [x] 5.6 Write property test for snapshot validation detection
    - **Property 11: Snapshot Validation Detection**
    - **Validates: Requirements 6.2, 6.3**

  - [x] 5.7 Write property test for optimistic locking
    - **Property 8: Event Store Optimistic Locking**
    - **Validates: Requirements 5.1**

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Refactor feature_flags module
  - [x] 7.1 Verify percentage rollout consistency
    - Ensure consistent hashing produces same result for same user
    - Add test for rollout monotonicity
    - _Requirements: 7.1, 7.2_

  - [x] 7.2 Write property test for percentage rollout consistency
    - **Property 12: Percentage Rollout Consistency**
    - **Validates: Requirements 7.1**

  - [x] 7.3 Write property test for rollout monotonicity
    - **Property 13: Rollout Monotonicity**
    - **Validates: Requirements 7.2**

  - [x] 7.4 Add audit trail support
    - Create `FlagAuditEvent` dataclass
    - Emit events on enable, disable, modify operations
    - Store audit history
    - _Requirements: 8.1, 8.2_

  - [x] 7.5 Write property test for audit event emission
    - **Property 14: Audit Event Emission**
    - **Validates: Requirements 8.1**

- [x] 8. Refactor fingerprint module
  - [x] 8.1 Add privacy controls
    - Implement configurable component exclusion
    - Ensure fingerprint valid without IP
    - _Requirements: 9.1, 9.2_

  - [x] 8.2 Write property test for fingerprint component exclusion
    - **Property 15: Fingerprint Component Exclusion**
    - **Validates: Requirements 9.1**

  - [x] 8.3 Write property test for fingerprint validity without IP
    - **Property 16: Fingerprint Validity Without IP**
    - **Validates: Requirements 9.2**

  - [x] 8.4 Verify hash algorithm and confidence indication
    - Ensure SHA-256 is used
    - Add low confidence indication
    - _Requirements: 10.1, 10.3_

  - [x] 8.5 Write property test for fingerprint hash algorithm
    - **Property 17: Fingerprint Hash Algorithm**
    - **Validates: Requirements 10.1**

  - [x] 8.6 Write property test for low confidence indication
    - **Property 18: Low Confidence Indication**
    - **Validates: Requirements 10.3**

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [x] 10. Refactor fuzzing module
  - [x] 10.1 Add config validation
    - Validate max_input_size >= min_input_size
    - Create directories if they don't exist
    - _Requirements: 11.1, 11.2, 11.3_

  - [x] 10.2 Write property test for fuzzing config validation
    - **Property 19: Fuzzing Config Validation**
    - **Validates: Requirements 11.1, 11.3**

  - [x] 10.3 Write property test for fuzzing directory creation
    - **Property 20: Fuzzing Directory Creation**
    - **Validates: Requirements 11.2**

  - [x] 10.4 Implement crash deduplication
    - Add `CrashSignature` class
    - Implement signature-based deduplication
    - Track occurrence counts
    - _Requirements: 12.1, 12.2, 12.3_

  - [x] 10.5 Write property test for crash signature uniqueness
    - **Property 21: Crash Signature Uniqueness**
    - **Validates: Requirements 12.1**

  - [x] 10.6 Write property test for duplicate crash counting
    - **Property 22: Duplicate Crash Counting**
    - **Validates: Requirements 12.2**

- [x] 11. Refactor generic_crud module
  - [x] 11.1 Add filter field validation
    - Validate filter fields against model fields
    - Validate sort fields against model fields
    - Return 400 for invalid fields
    - _Requirements: 13.1, 13.2_

  - [x] 11.2 Write property test for filter field validation
    - **Property 23: Filter Field Validation**
    - **Validates: Requirements 13.1, 13.2**

  - [x] 11.3 Add malformed JSON handling
    - Catch JSON parse errors
    - Return 400 Bad Request with safe message
    - _Requirements: 13.3_

  - [x] 11.4 Write property test for malformed JSON handling
    - **Property 24: Malformed JSON Handling**
    - **Validates: Requirements 13.3**

  - [x] 11.5 Enforce pagination cap
    - Cap per_page at 100
    - Handle large offsets gracefully
    - _Requirements: 14.1, 14.2_

  - [x] 11.6 Write property test for pagination cap enforcement
    - **Property 25: Pagination Cap Enforcement**
    - **Validates: Requirements 14.1**

- [x] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Refactor graphql_federation module
  - [x] 13.1 Add key field validation
    - Verify @key fields exist in entity
    - Return validation error if missing
    - _Requirements: 15.1_

  - [x] 13.2 Write property test for federation key field validation
    - **Property 26: Federation Key Field Validation**
    - **Validates: Requirements 15.1**

  - [x] 13.3 Add requires/external validation
    - Verify @requires references @external fields
    - Return validation error if not external
    - _Requirements: 15.2_

  - [x] 13.4 Write property test for federation requires external validation
    - **Property 27: Federation Requires External Validation**
    - **Validates: Requirements 15.2**

  - [x] 13.5 Return all validation errors
    - Collect all errors instead of failing on first
    - Return complete error list
    - _Requirements: 15.3_

  - [x] 13.6 Write property test for federation all errors returned
    - **Property 28: Federation All Errors Returned**
    - **Validates: Requirements 15.3**

  - [x] 13.7 Add entity resolution validation
    - Validate representation format
    - Return clear error for missing resolver
    - _Requirements: 16.1, 16.2_

  - [x] 13.8 Write property test for entity resolution validation
    - **Property 29: Entity Resolution Validation**
    - **Validates: Requirements 16.1**

  - [x] 13.9 Write property test for missing resolver error
    - **Property 30: Missing Resolver Error**
    - **Validates: Requirements 16.2**

- [x] 14. Refactor hot_reload module
  - [x] 14.1 Add state preservation on failure
    - Preserve previous module state on reload failure
    - Log error and continue
    - _Requirements: 17.2_

  - [x] 14.2 Write property test for hot reload state preservation
    - **Property 31: Hot Reload State Preservation**
    - **Validates: Requirements 17.2**

  - [x] 14.3 Add syntax error handling
    - Catch syntax errors during reload
    - Skip module and log error
    - _Requirements: 17.3_

  - [x] 14.4 Write property test for syntax error handling
    - **Property 32: Syntax Error Handling**
    - **Validates: Requirements 17.3**

  - [x] 14.5 Implement dependency cascade reload
    - Track module dependencies
    - Reload dependents when module changes
    - _Requirements: 18.1_

  - [x] 14.6 Write property test for dependency cascade reload
    - **Property 33: Dependency Cascade Reload**
    - **Validates: Requirements 18.1**

  - [x] 14.7 Handle circular dependencies
    - Detect circular dependencies
    - Terminate without infinite loop
    - _Requirements: 18.2_

  - [x] 14.8 Write property test for circular dependency termination
    - **Property 34: Circular Dependency Termination**
    - **Validates: Requirements 18.2**

- [x] 15. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 16. Refactor contract_testing module
  - [x] 16.1 Add nested field path validation
    - Support dot notation for nested fields
    - Support array index access
    - _Requirements: 19.1, 19.2_

  - [x] 16.2 Write property test for nested field path validation
    - **Property 35: Nested Field Path Validation**
    - **Validates: Requirements 19.1**

  - [x] 16.3 Write property test for array index access
    - **Property 36: Array Index Access**
    - **Validates: Requirements 19.2**

  - [x] 16.4 Improve OpenAPI path parameter matching
    - Support parameterized paths correctly
    - Handle multiple parameters
    - _Requirements: 20.2_

  - [x] 16.5 Write property test for OpenAPI path parameter matching
    - **Property 37: OpenAPI Path Parameter Matching**
    - **Validates: Requirements 20.2**

- [x] 17. Clean up unused imports
  - [x] 17.1 Remove unused imports from connection_pool/enums.py
    - Remove: ABC, abstractmethod, dataclass, field, datetime, timedelta, Any, Generic, Protocol, TypeVar, runtime_checkable
    - Keep only: Enum
    - _Requirements: 21.1, 21.2, 21.3_

  - [x] 17.2 Remove unused imports from feature_flags/enums.py
    - Remove: hashlib, random, dataclass, field, datetime, timezone, Any, Callable, BaseModel
    - Keep only: Enum
    - _Requirements: 21.1, 21.2, 21.3_

  - [x] 17.3 Remove unused imports from feature_flags/models.py
    - Remove: hashlib, random, datetime, timezone, Enum, Callable, BaseModel
    - Keep only: dataclass, field, Any, and local imports
    - _Requirements: 21.1, 21.2, 21.3_

  - [x] 17.4 Remove unused imports from feature_flags/config.py
    - Remove: hashlib, random, Enum, Callable, BaseModel
    - Keep only: dataclass, field, datetime, timezone, Any, and local imports
    - _Requirements: 21.1, 21.2, 21.3_

  - [x] 17.5 Remove unused imports from graphql_federation/enums.py
    - Remove: dataclass, field, Any, Protocol, runtime_checkable
    - Keep only: Enum, __future__ annotations
    - _Requirements: 21.1, 21.2, 21.3_

  - [x] 17.6 Remove unused imports from connection_pool/models.py
    - Remove: asyncio, ABC, abstractmethod, timedelta, Enum, Any, Generic, Protocol, TypeVar, runtime_checkable, BaseModel
    - Keep only: dataclass, field, datetime, timezone, and local imports
    - _Requirements: 21.1, 21.2, 21.3_

- [x] 18. Final Checkpoint - Ensure all tests pass

  - Ensure all tests pass, ask the user if questions arise.
