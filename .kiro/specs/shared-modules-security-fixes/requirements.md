# Requirements Document

## Introduction

This specification addresses critical security vulnerabilities and code quality issues identified during a comprehensive code review of the `src/my_api/shared/` modules. The fixes are prioritized by severity, focusing first on security-critical issues (cryptography, hashing), then on deprecated API usage, and finally on code quality improvements.

## Glossary

- **Shared_Modules**: The collection of reusable Python modules in `src/my_api/shared/`
- **AES-GCM**: Advanced Encryption Standard in Galois/Counter Mode, an authenticated encryption algorithm
- **Bcrypt**: A password-hashing function designed for secure credential storage
- **Salt**: Random data used as additional input to a one-way function that hashes data
- **Rainbow Table**: A precomputed table for caching the output of cryptographic hash functions
- **XOR Encryption**: A trivially breakable encryption method using exclusive-or operation
- **Context Variable**: Python's contextvars for managing context-local state in async code

## Requirements

### Requirement 1: Secure Field Encryption

**User Story:** As a security engineer, I want field-level encryption to use industry-standard cryptographic algorithms, so that sensitive data is protected against known attacks.

#### Acceptance Criteria

1. WHEN the FieldEncryptor encrypts data THEN the system SHALL use AES-256-GCM from the cryptography library
2. WHEN the FieldEncryptor decrypts data THEN the system SHALL verify the authentication tag before returning plaintext
3. WHEN encryption fails due to invalid key THEN the system SHALL raise a specific EncryptionError with context
4. WHEN the XOR-based encryption method is called THEN the system SHALL raise DeprecationWarning

### Requirement 2: Secure API Key Hashing

**User Story:** As a security engineer, I want API keys to be hashed with salt, so that they are protected against rainbow table attacks.

#### Acceptance Criteria

1. WHEN an API key is created THEN the system SHALL hash it using bcrypt with a cost factor of at least 12
2. WHEN an API key is validated THEN the system SHALL use constant-time comparison to prevent timing attacks
3. WHEN the hash function is called THEN the system SHALL generate a unique salt for each key
4. WHEN migrating existing keys THEN the system SHALL support both old SHA256 and new bcrypt formats

### Requirement 3: Datetime API Modernization

**User Story:** As a developer, I want all datetime operations to use timezone-aware APIs, so that the codebase is compatible with Python 3.12+ and avoids deprecation warnings.

#### Acceptance Criteria

1. WHEN creating a current timestamp THEN the system SHALL use datetime.now(timezone.utc) instead of datetime.utcnow()
2. WHEN comparing timestamps THEN the system SHALL ensure both timestamps are timezone-aware
3. WHEN serializing timestamps THEN the system SHALL include timezone information in ISO 8601 format

### Requirement 4: Regex Injection Prevention

**User Story:** As a security engineer, I want path pattern matching to be safe from regex injection, so that malicious patterns cannot cause ReDoS attacks.

#### Acceptance Criteria

1. WHEN converting glob patterns to regex THEN the system SHALL escape all special regex characters before conversion
2. WHEN compiling user-provided patterns THEN the system SHALL set a timeout or use re2 for safe matching
3. WHEN an invalid pattern is provided THEN the system SHALL raise PatternValidationError with details

### Requirement 5: Circuit Breaker Registry Refactoring

**User Story:** As a developer, I want the circuit breaker registry to be thread-safe and testable, so that it works correctly in concurrent environments and tests are isolated.

#### Acceptance Criteria

1. WHEN accessing the circuit breaker registry THEN the system SHALL use a singleton pattern with thread-safe initialization
2. WHEN running tests THEN the system SHALL provide a method to reset or isolate the registry state
3. WHEN multiple threads access the registry THEN the system SHALL prevent race conditions using locks

### Requirement 6: Context Variable Safety

**User Story:** As a developer, I want correlation context management to handle edge cases safely, so that context leaks and reset errors are prevented.

#### Acceptance Criteria

1. WHEN exiting a correlation context THEN the system SHALL safely reset tokens even if already reset
2. WHEN a context manager is used incorrectly THEN the system SHALL log a warning and recover gracefully
3. WHEN nested contexts are used THEN the system SHALL maintain proper parent-child relationships

### Requirement 7: Code Quality Improvements

**User Story:** As a developer, I want the shared modules to follow PEP8 and modern Python best practices, so that the codebase is maintainable and consistent.

#### Acceptance Criteria

1. WHEN code is committed THEN the system SHALL have no lines exceeding 120 characters
2. WHEN imports are declared THEN the system SHALL not include unused imports
3. WHEN magic numbers are used THEN the system SHALL define them as named constants
4. WHEN encoding data THEN the system SHALL explicitly specify UTF-8 encoding
