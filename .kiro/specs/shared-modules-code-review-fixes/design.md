# Design Document - Shared Modules Code Review Fixes

## Overview

Este documento descreve o design das correções identificadas durante o code review dos módulos compartilhados. As correções abordam problemas de segurança, performance, manutenibilidade e conformidade com boas práticas Python.

## Architecture

A arquitetura existente dos módulos será mantida. As correções são incrementais e não alteram a estrutura fundamental:

```
src/my_api/shared/
├── request_signing/     # Correções: imports, secret key validation
├── response_transformation/  # Correções: imports cleanup
├── saga/                # Sem alterações necessárias
├── secrets_manager/     # Correções: providers.py, logging
├── streaming/           # Correções: imports cleanup
├── tiered_rate_limiter/ # Sem alterações necessárias
├── utils/               # Correções: exports expansion
└── waf/                 # Correções: timezone, ReDoS protection
```

## Components and Interfaces

### 1. BaseSecretsProvider (Abstract Base Class)

```python
class BaseSecretsProvider(ABC):
    """Abstract base class for secrets providers."""
    
    @abstractmethod
    async def get_secret(self, name: str, version: str | None = None) -> SecretValue:
        """Get a secret by name."""
        ...
    
    @abstractmethod
    async def create_secret(
        self, name: str, value: str | dict, secret_type: SecretType
    ) -> SecretMetadata:
        """Create a new secret."""
        ...
    
    @abstractmethod
    async def update_secret(self, name: str, value: str | dict) -> SecretMetadata:
        """Update an existing secret."""
        ...
    
    @abstractmethod
    async def delete_secret(self, name: str, force: bool = False) -> bool:
        """Delete a secret."""
        ...
    
    @abstractmethod
    async def rotate_secret(self, name: str) -> SecretMetadata:
        """Rotate a secret."""
        ...
```

### 2. LocalSecretsProvider (Concrete Implementation)

```python
class LocalSecretsProvider(BaseSecretsProvider):
    """Local in-memory secrets provider for development/testing."""
    
    def __init__(self) -> None:
        self._secrets: dict[str, SecretValue] = {}
```

### 3. RequestSigner/RequestVerifier (Enhanced)

```python
MIN_SECRET_KEY_LENGTH = 32  # 256 bits minimum

class RequestSigner:
    def __init__(self, secret_key: str | bytes, config: SignatureConfig | None = None):
        # Validates key length >= MIN_SECRET_KEY_LENGTH
        ...
```

## Data Models

### SecretMetadata (Existing)

```python
@dataclass(frozen=True)
class SecretMetadata:
    name: str
    version: str = "AWSCURRENT"
    created_at: datetime  # UTC timezone-aware
    updated_at: datetime  # UTC timezone-aware
    rotation_enabled: bool = False
    next_rotation: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)
```

### ThreatDetection (Modified)

```python
@dataclass
class ThreatDetection:
    detected: bool
    rule: WAFRule | None = None
    matched_value: str | None = None
    target: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))  # UTC
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Secret CRUD Round-Trip Consistency

*For any* valid secret name and value, creating a secret and then retrieving it should return the same value, and the metadata should contain valid timestamps.

**Validates: Requirements 1.3, 1.4, 1.5**

### Property 2: Secret Not Found Error

*For any* non-existent secret name, calling get_secret should raise SecretNotFoundError containing the secret name.

**Validates: Requirements 1.3**

### Property 3: Timezone Preservation

*For any* ThreatDetection instance created, the timestamp field should be timezone-aware and in UTC.

**Validates: Requirements 4.1, 4.3**

### Property 4: Secret Key Minimum Length Validation

*For any* secret key shorter than 32 bytes, instantiating RequestSigner or RequestVerifier should raise ValueError with a message containing the minimum required length.

**Validates: Requirements 6.1, 6.2, 6.3**

### Property 5: ReDoS Protection - Bounded Pattern Matching

*For any* input string longer than 100 characters between SQL keywords, the WAF SQL injection patterns should not cause excessive backtracking (pattern should complete in bounded time).

**Validates: Requirements 5.1**

### Property 6: Utils Module Exports Completeness

*For any* public function in utils submodules (datetime, ids, pagination, password, sanitization), the function should be accessible via direct import from utils.

**Validates: Requirements 8.1**

## Error Handling

### Exception Hierarchy

```
SecretsError (base)
├── SecretNotFoundError
├── SecretAccessDeniedError
└── SecretRotationError

SignatureError (base)
├── InvalidSignatureError
├── ExpiredTimestampError
└── ReplayedRequestError

ValueError (builtin)
└── Used for secret key length validation
```

### Logging Strategy

```python
import logging

_logger = logging.getLogger(__name__)

# Success logging
_logger.info("Secret rotated successfully", extra={"secret_name": name})

# Error logging with full context
_logger.exception("Secret rotation failed", extra={"secret_name": name})
```

## Testing Strategy

### Dual Testing Approach

O projeto utiliza tanto testes unitários quanto property-based testing para garantir correção:

1. **Unit Tests**: Verificam exemplos específicos e edge cases
2. **Property-Based Tests**: Verificam propriedades universais usando Hypothesis

### Property-Based Testing Framework

- **Framework**: Hypothesis (já configurado no projeto)
- **Minimum iterations**: 100 por propriedade
- **Tag format**: `**Feature: shared-modules-code-review-fixes, Property {number}: {property_text}**`

### Test Structure

```python
from hypothesis import given, strategies as st, settings

@settings(max_examples=100)
@given(secret_name=st.text(min_size=1, max_size=50))
def test_secret_not_found_error(secret_name: str):
    """
    **Feature: shared-modules-code-review-fixes, Property 2: Secret Not Found Error**
    **Validates: Requirements 1.3**
    """
    provider = LocalSecretsProvider()
    with pytest.raises(SecretNotFoundError) as exc_info:
        await provider.get_secret(secret_name)
    assert secret_name in str(exc_info.value)
```

### Unit Test Coverage

- Secrets provider instantiation and basic operations
- Logging verification with mock logger
- Import structure verification
- Regex pattern compilation error handling
