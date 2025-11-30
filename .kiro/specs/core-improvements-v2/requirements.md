# Requirements Document

## Introduction

Este documento especifica os requisitos para melhorias adicionais no módulo `src/my_api/core`, identificadas através de um code review abrangente. As melhorias focam em thread-safety, gerenciamento de memória, fail-closed behavior, e qualidade de código seguindo as melhores práticas Python, PEP8, OWASP e padrões modernos FastAPI.

## Glossary

- **Thread-Safety**: Garantia de que código pode ser executado por múltiplas threads simultaneamente sem race conditions
- **Double-Check Locking**: Padrão de inicialização lazy thread-safe que verifica a condição duas vezes
- **Fail-Closed**: Comportamento de segurança onde falhas resultam em negação de acesso ao invés de permissão
- **Memory Leak**: Crescimento contínuo de uso de memória devido a dados não liberados
- **Correlation ID**: Identificador único para rastreamento de requisições através do sistema
- **PII**: Personally Identifiable Information - dados que podem identificar um indivíduo
- **GDPR**: General Data Protection Regulation - regulamento europeu de proteção de dados

## Requirements

### Requirement 1: Thread-Safe Singleton Patterns

**User Story:** As a developer, I want global singletons to be thread-safe, so that the application works correctly under concurrent load.

#### Acceptance Criteria

1. WHEN multiple threads call get_rbac_service() simultaneously THEN the RBACService SHALL return the same instance without race conditions
2. WHEN multiple threads call get_password_validator() simultaneously THEN the PasswordValidator SHALL return the same instance without race conditions
3. WHEN multiple threads call get_audit_logger() simultaneously THEN the SecurityAuditLogger SHALL return the same instance without race conditions
4. WHEN initializing singletons THEN the module SHALL use double-check locking pattern with threading.Lock
5. WHEN a singleton is already initialized THEN subsequent calls SHALL NOT acquire the lock (performance optimization)

### Requirement 2: JWT Refresh Token Memory Management

**User Story:** As a system administrator, I want refresh token tracking to have bounded memory usage, so that the application doesn't run out of memory in production.

#### Acceptance Criteria

1. WHEN tracking used refresh tokens THEN the JWTService SHALL limit the number of tracked tokens to a configurable maximum
2. WHEN the token tracking limit is reached THEN the JWTService SHALL remove the oldest tokens first (FIFO)
3. WHEN a token expires naturally THEN the JWTService SHALL remove it from tracking during cleanup
4. WHEN cleanup runs THEN the JWTService SHALL remove all expired tokens before checking the limit
5. WHEN configuring the service THEN the JWTService SHALL accept a max_tracked_tokens parameter with sensible default

### Requirement 3: JWT Validator Fail-Closed Behavior

**User Story:** As a security engineer, I want token validation to fail closed when the revocation store is unavailable, so that compromised tokens cannot be used during outages.

#### Acceptance Criteria

1. WHEN the revocation store raises an exception THEN validate_with_revocation() SHALL reject the token
2. WHEN the revocation store is unavailable THEN the JWTValidator SHALL log the error with details
3. WHEN rejecting due to store unavailability THEN the JWTValidator SHALL raise InvalidTokenError with appropriate message
4. WHEN the revocation store returns successfully THEN normal validation SHALL proceed
5. WHEN InvalidTokenError is raised by validation THEN it SHALL be re-raised without modification

### Requirement 4: Audit Logger Correlation ID Support

**User Story:** As a compliance officer, I want all security events to include correlation IDs, so that I can trace events across the system.

#### Acceptance Criteria

1. WHEN creating SecurityAuditLogger THEN the class SHALL accept an optional correlation_id_provider callable
2. WHEN logging any security event THEN the event SHALL include a correlation_id field
3. WHEN no correlation_id_provider is configured THEN the logger SHALL generate a new ULID for each event
4. WHEN a correlation_id_provider is configured THEN the logger SHALL use it to obtain the correlation ID
5. WHEN serializing SecurityEvent THEN to_dict() SHALL include the correlation_id field

### Requirement 5: Enhanced PII Redaction Patterns

**User Story:** As a compliance officer, I want comprehensive PII redaction, so that sensitive data is protected in logs.

#### Acceptance Criteria

1. WHEN redacting PII THEN the SecurityAuditLogger SHALL support configurable IP address redaction
2. WHEN redacting PII THEN the SecurityAuditLogger SHALL detect Bearer tokens in Authorization headers
3. WHEN redacting PII THEN the SecurityAuditLogger SHALL detect credit cards with various separators (spaces, dashes)
4. WHEN redacting PII THEN the SecurityAuditLogger SHALL detect international phone number formats
5. WHEN IP redaction is enabled THEN both IPv4 and IPv6 addresses SHALL be redacted

### Requirement 6: Module Public API Exports

**User Story:** As a developer, I want clear module exports, so that I know which classes and functions are part of the public API.

#### Acceptance Criteria

1. WHEN importing from exceptions module THEN __all__ SHALL list all public exception classes
2. WHEN importing from config module THEN __all__ SHALL list Settings, get_settings, and utility functions
3. WHEN importing from container module THEN __all__ SHALL list Container, LifecycleManager, and factory functions
4. WHEN a class is not in __all__ THEN it SHALL be considered internal implementation detail
5. WHEN adding new public classes THEN __all__ SHALL be updated accordingly

### Requirement 7: Container Redis URL Configuration

**User Story:** As a developer, I want Redis configuration to use dedicated settings, so that the container doesn't make fragile assumptions about URL formats.

#### Acceptance Criteria

1. WHEN configuring Redis cache THEN the Container SHALL use RedisSettings.url instead of deriving from database URL
2. WHEN Redis is not configured THEN the Container SHALL fall back to a sensible default URL
3. WHEN Redis settings exist THEN the Container SHALL respect the enabled flag
4. WHEN accessing Redis URL THEN the Container SHALL NOT modify or transform the URL
5. WHEN Redis is disabled THEN the Container SHALL use in-memory cache instead

### Requirement 8: Code Quality Constants

**User Story:** As a developer, I want magic numbers replaced with named constants, so that the code is more maintainable.

#### Acceptance Criteria

1. WHEN defining password strength scoring THEN the module SHALL use named constants for score values
2. WHEN defining maximum values THEN the module SHALL use Final type hints for immutability
3. WHEN using regex patterns THEN the module SHALL define them as module-level constants with Final
4. WHEN calculating scores THEN the code SHALL reference named constants instead of literal numbers
5. WHEN documenting constants THEN each constant SHALL have a descriptive comment

