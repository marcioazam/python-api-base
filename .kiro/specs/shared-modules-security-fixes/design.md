# Design Document

## Overview

This design addresses security vulnerabilities and code quality issues in the shared modules. The primary focus is on replacing insecure cryptographic implementations with industry-standard alternatives, modernizing deprecated datetime APIs, and improving code safety patterns.

The fixes are prioritized by severity:
1. **Critical**: Replace XOR encryption with AES-256-GCM (CWE-327)
2. **High**: Implement bcrypt for API key hashing with salts (CWE-916)
3. **Medium**: Regex injection prevention for ReDoS attacks (CWE-1333)
4. **Medium**: Thread-safe circuit breaker registry
5. **Low**: Context variable safety improvements
6. **Low**: Code quality and PEP8 compliance

## Architecture

The fixes are organized into three layers:

```
┌─────────────────────────────────────────────────────────┐
│                    Shared Modules                        │
├─────────────────────────────────────────────────────────┤
│  Security Layer                                          │
│  ├── field_encryption.py (AES-256-GCM)                  │
│  ├── api_key_service.py (bcrypt hashing)                │
│  └── waf/patterns.py (safe regex)                       │
├─────────────────────────────────────────────────────────┤
│  Compatibility Layer                                     │
│  ├── utils/datetime.py (timezone-aware)                 │
│  └── All modules using datetime                         │
├─────────────────────────────────────────────────────────┤
│  Safety Layer                                            │
│  ├── circuit_breaker.py (thread-safe registry)          │
│  └── correlation.py (context variable safety)           │
└─────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Secure Field Encryption (`field_encryption.py`)

**Current State**: Uses XOR-based encryption which is trivially breakable.

**Target State**: AES-256-GCM authenticated encryption using the `cryptography` library.

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dataclasses import dataclass
from enum import Enum

class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""
    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}

class FieldEncryptor:
    """AES-256-GCM field-level encryption service."""
    
    NONCE_SIZE = 12  # 96 bits for GCM
    KEY_SIZE = 32    # 256 bits
    TAG_SIZE = 16    # 128 bits
    
    async def encrypt(self, plaintext: str | bytes) -> EncryptedValue:
        """Encrypt using AES-256-GCM with authenticated encryption."""
        ...
    
    async def decrypt(self, encrypted: EncryptedValue) -> bytes:
        """Decrypt and verify authentication tag."""
        ...
    
    @deprecated("Use encrypt() with AES-256-GCM instead")
    def _xor_encrypt(self, data: bytes, key: bytes, nonce: bytes) -> bytes:
        """Deprecated XOR encryption - raises DeprecationWarning."""
        warnings.warn(
            "XOR encryption is insecure. Use AES-256-GCM.",
            DeprecationWarning,
            stacklevel=2
        )
        raise EncryptionError("XOR encryption is deprecated and disabled")
```

**Design Decisions**:
- Use `cryptography` library (FIPS-validated, well-audited)
- AES-256-GCM provides both confidentiality and integrity
- 96-bit nonce (recommended for GCM)
- Deprecate XOR method with warning, then raise error

### 2. Secure API Key Hashing (`api_key_service.py`)

**Current State**: Uses SHA256 without salt, vulnerable to rainbow table attacks.

**Target State**: bcrypt with cost factor 12+ and constant-time comparison.

```python
import bcrypt
import hmac

class APIKeyService:
    """Service for managing API keys with secure hashing."""
    
    BCRYPT_COST_FACTOR = 12
    HASH_PREFIX_BCRYPT = "$2b$"
    HASH_PREFIX_SHA256 = "sha256:"
    
    def _hash_key(self, key: str) -> str:
        """Hash API key using bcrypt with unique salt."""
        salt = bcrypt.gensalt(rounds=self.BCRYPT_COST_FACTOR)
        return bcrypt.hashpw(key.encode("utf-8"), salt).decode("utf-8")
    
    def _verify_key(self, key: str, key_hash: str) -> bool:
        """Verify key using constant-time comparison."""
        if key_hash.startswith(self.HASH_PREFIX_BCRYPT):
            return bcrypt.checkpw(key.encode("utf-8"), key_hash.encode("utf-8"))
        elif key_hash.startswith(self.HASH_PREFIX_SHA256):
            # Legacy support for migration
            computed = hashlib.sha256(key.encode("utf-8")).hexdigest()
            return hmac.compare_digest(computed, key_hash[7:])
        return False
```

**Design Decisions**:
- bcrypt cost factor 12 (balances security and performance)
- Support both bcrypt and SHA256 for migration period
- Use `hmac.compare_digest` for constant-time comparison
- Each key gets unique salt (bcrypt default behavior)

### 3. Regex Injection Prevention (`waf/patterns.py`)

**Current State**: Some patterns may be vulnerable to ReDoS.

**Target State**: Safe patterns with bounded quantifiers and optional re2 support.

```python
import re
from typing import Pattern
from functools import lru_cache

class PatternValidationError(Exception):
    """Raised when pattern validation fails."""
    def __init__(self, pattern: str, reason: str):
        super().__init__(f"Invalid pattern '{pattern}': {reason}")
        self.pattern = pattern
        self.reason = reason

class SafePatternCompiler:
    """Compile regex patterns safely with ReDoS prevention."""
    
    MAX_PATTERN_LENGTH = 1000
    DANGEROUS_PATTERNS = [
        r"(.+)+",      # Nested quantifiers
        r"(.*)*",      # Nested quantifiers
        r"([^x]+)+",   # Nested quantifiers with negation
    ]
    
    @classmethod
    def compile(cls, pattern: str, timeout_ms: int = 100) -> Pattern[str]:
        """Compile pattern with safety checks."""
        cls._validate_pattern(pattern)
        return re.compile(pattern)
    
    @classmethod
    def glob_to_regex(cls, glob_pattern: str) -> str:
        """Convert glob pattern to regex, escaping special chars."""
        # Escape all regex special characters first
        escaped = re.escape(glob_pattern)
        # Then convert glob wildcards
        escaped = escaped.replace(r"\*", ".*")
        escaped = escaped.replace(r"\?", ".")
        return f"^{escaped}$"
```

**Design Decisions**:
- Validate patterns before compilation
- Use bounded quantifiers (`.{0,100}` instead of `.*`)
- Provide `glob_to_regex` with proper escaping
- Pattern length limits to prevent abuse

### 4. Thread-Safe Circuit Breaker Registry (`circuit_breaker.py`)

**Current State**: Global dictionary without thread safety.

**Target State**: Thread-safe singleton with test isolation support.

```python
import threading
from typing import ClassVar

class CircuitBreakerRegistry:
    """Thread-safe singleton registry for circuit breakers."""
    
    _instance: ClassVar["CircuitBreakerRegistry | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()
    
    def __new__(cls) -> "CircuitBreakerRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._breakers = {}
                    cls._instance._breakers_lock = threading.RLock()
        return cls._instance
    
    def get(self, name: str, config: CircuitBreakerConfig | None = None) -> CircuitBreaker:
        """Get or create circuit breaker (thread-safe)."""
        with self._breakers_lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
            return self._breakers[name]
    
    def reset(self) -> None:
        """Reset registry for testing."""
        with self._breakers_lock:
            self._breakers.clear()
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance for test isolation."""
        with cls._lock:
            cls._instance = None
```

**Design Decisions**:
- Double-checked locking for singleton
- RLock for nested operations
- Explicit reset methods for test isolation
- Backward-compatible module-level functions

### 5. Context Variable Safety (`correlation.py`)

**Current State**: Token reset may fail if already reset.

**Target State**: Safe token handling with graceful recovery.

```python
import contextvars
import logging

logger = logging.getLogger(__name__)

class CorrelationContextManager:
    """Context manager with safe token handling."""
    
    def __exit__(self, *args: Any) -> None:
        """Exit context with safe token reset."""
        for token in reversed(self._tokens):
            try:
                if hasattr(token, "var"):
                    token.var.reset(token)
            except ValueError:
                # Token already reset - log and continue
                logger.warning(
                    "Correlation context token already reset",
                    extra={"token_var": getattr(token, "var", None)}
                )
        self._tokens.clear()
```

**Design Decisions**:
- Catch ValueError on token reset
- Log warnings for debugging
- Continue processing remaining tokens
- Clear token list regardless of errors

### 6. Datetime API Modernization

**Current State**: Some modules may use deprecated `datetime.utcnow()`.

**Target State**: All datetime operations use timezone-aware APIs.

The `utils/datetime.py` module already provides correct implementations. Ensure all modules use these utilities:

```python
from my_api.shared.utils.datetime import utc_now, ensure_utc, to_iso8601

# Instead of: datetime.utcnow()
# Use: utc_now()

# Instead of: dt.isoformat()
# Use: to_iso8601(dt)
```

## Data Models

### EncryptedValue (Updated)

```python
@dataclass
class EncryptedValue:
    """Encrypted value with AES-GCM metadata."""
    ciphertext: bytes
    key_id: str
    algorithm: EncryptionAlgorithm  # Must be AES_256_GCM
    nonce: bytes                     # 12 bytes for GCM
    tag: bytes                       # 16 bytes authentication tag
    version: int = 2                 # Version 2 for AES-GCM
```

### APIKey (Updated)

```python
@dataclass
class APIKey:
    """API key with bcrypt hash."""
    key_id: str
    key_hash: str          # bcrypt hash (starts with $2b$)
    hash_version: int = 2  # 1=SHA256, 2=bcrypt
    # ... other fields unchanged
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Encryption Round-Trip with Authentication

*For any* plaintext data, encrypting with AES-256-GCM and then decrypting should return the original plaintext, and tampering with the ciphertext or tag should cause decryption to fail with an authentication error.

**Validates: Requirements 1.1, 1.2**

### Property 2: Bcrypt Hash Uniqueness

*For any* API key, hashing it multiple times should produce different hashes (due to unique salts), and all hashes should verify correctly against the original key.

**Validates: Requirements 2.1, 2.3**

### Property 3: Hash Format Migration Compatibility

*For any* API key, the system should correctly validate both legacy SHA256 hashes and new bcrypt hashes, allowing seamless migration.

**Validates: Requirements 2.4**

### Property 4: Timestamp Timezone Awareness

*For any* timestamp created or serialized by the system, it should be timezone-aware (have tzinfo set to UTC) and serialize with timezone information in ISO 8601 format.

**Validates: Requirements 3.1, 3.2, 3.3**

### Property 5: Glob-to-Regex Safe Conversion

*For any* glob pattern containing special regex characters, converting to regex should properly escape those characters, preventing regex injection.

**Validates: Requirements 4.1**

### Property 6: Circuit Breaker Registry Thread Safety

*For any* sequence of concurrent get/create operations on the circuit breaker registry, the same circuit breaker instance should be returned for the same name, with no race conditions or duplicate instances.

**Validates: Requirements 5.1, 5.3**

### Property 7: Context Token Safe Reset

*For any* correlation context, exiting the context (even multiple times) should not raise exceptions and should properly restore previous context values.

**Validates: Requirements 6.1, 6.3**

## Error Handling

### New Exception Types

```python
class EncryptionError(Exception):
    """Base encryption error with context."""
    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}

class DecryptionError(EncryptionError):
    """Decryption failed (invalid key, corrupted data, auth failure)."""
    pass

class AuthenticationError(DecryptionError):
    """Authentication tag verification failed."""
    pass

class PatternValidationError(ValueError):
    """Invalid regex pattern."""
    def __init__(self, pattern: str, reason: str):
        super().__init__(f"Invalid pattern '{pattern}': {reason}")
        self.pattern = pattern
        self.reason = reason
```

### Error Handling Strategy

| Error Type | Handling | Logging |
|------------|----------|---------|
| Invalid encryption key | Raise `EncryptionError` | ERROR with key_id |
| Auth tag mismatch | Raise `AuthenticationError` | WARNING (potential tampering) |
| Deprecated XOR call | Raise `DeprecationWarning` then `EncryptionError` | WARNING |
| Invalid regex pattern | Raise `PatternValidationError` | WARNING with pattern |
| Token already reset | Log and continue | WARNING |

## Testing Strategy

### Dual Testing Approach

Both unit tests and property-based tests are required:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all valid inputs

### Property-Based Testing

**Library**: Hypothesis (Python)

**Configuration**: Minimum 100 iterations per property test

**Test Annotations**: Each property test must reference the design property:
```python
# **Feature: shared-modules-security-fixes, Property 1: Encryption Round-Trip with Authentication**
# **Validates: Requirements 1.1, 1.2**
@given(plaintext=st.binary(min_size=1, max_size=10000))
@settings(max_examples=100)
def test_encryption_round_trip(plaintext: bytes) -> None:
    ...
```

### Unit Test Coverage

| Component | Test Focus |
|-----------|------------|
| FieldEncryptor | Invalid keys, empty data, large data, algorithm selection |
| APIKeyService | Key creation, validation, rotation, migration |
| SafePatternCompiler | Dangerous patterns, edge cases, glob conversion |
| CircuitBreakerRegistry | Concurrent access, reset, isolation |
| CorrelationContextManager | Nested contexts, double exit, error recovery |

### Security Testing

- Verify XOR encryption raises DeprecationWarning
- Verify bcrypt cost factor >= 12
- Verify constant-time comparison is used
- Verify ReDoS patterns are rejected
- Verify authentication tag is verified before decryption

## Migration Strategy

### Phase 1: Add New Implementations (Non-Breaking)
- Add AES-256-GCM encryption alongside XOR
- Add bcrypt hashing alongside SHA256
- Add deprecation warnings

### Phase 2: Migrate Existing Data
- Re-encrypt existing data with AES-256-GCM
- Re-hash API keys with bcrypt (on next validation)
- Update version fields

### Phase 3: Remove Deprecated Code
- Remove XOR encryption (after migration complete)
- Remove SHA256 hashing support (after all keys migrated)

## Dependencies

### New Dependencies

```toml
[project.dependencies]
cryptography = ">=41.0.0"  # AES-GCM implementation
bcrypt = ">=4.0.0"         # Password hashing
```

### Existing Dependencies (No Changes)
- `pendulum` - Already used for datetime
- `hypothesis` - Already used for property testing
