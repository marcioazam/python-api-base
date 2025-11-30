# Requirements Document

## Introduction

Este documento define os requisitos para transformar o projeto my-api na **Melhor API Base Python de 2025**. O objetivo é consolidar todas as melhorias pendentes, eliminar código legado/depreciado, garantir 100% de conformidade com padrões modernos (PEP 695, OWASP 2023, Clean Architecture), maximizar reuso de código através de generics, e assegurar performance e segurança de nível enterprise.

Este MEGA SPEC consolida e finaliza todas as specs anteriores, criando uma base de API definitiva que serve como referência para projetos Python modernos.

## Glossary

- **API_Base**: Framework genérico reutilizável para construção de APIs REST com FastAPI
- **PEP_695**: Python Enhancement Proposal para nova sintaxe de type parameters (Python 3.12+)
- **OWASP_API_Top_10**: Lista das 10 principais vulnerabilidades de segurança em APIs (edição 2023)
- **Clean_Architecture**: Padrão arquitetural com separação em camadas (Domain, Application, Infrastructure, Adapters)
- **DDD**: Domain-Driven Design - abordagem de design focada no domínio de negócio
- **Property_Based_Testing**: Técnica de teste que verifica propriedades universais usando geração automática de dados
- **Hypothesis**: Biblioteca Python para property-based testing
- **Generic_CRUD**: Operações Create, Read, Update, Delete implementadas de forma genérica e reutilizável
- **Result_Pattern**: Padrão funcional para tratamento de erros sem exceções (Ok/Err)
- **Unit_of_Work**: Padrão para gerenciamento de transações de banco de dados
- **Circuit_Breaker**: Padrão de resiliência para falhas em serviços externos
- **OpenTelemetry**: Framework de observabilidade para traces, métricas e logs
- **SecretStr**: Tipo Pydantic que oculta valores sensíveis em logs e repr

## Requirements

### Requirement 1: Generic Type System Compliance (VERIFIED ✅)

**User Story:** As a developer, I want all generic classes to use PEP 695 syntax, so that the codebase follows Python 3.12+ modern standards and provides better type inference.

**Status:** O código já está 100% em conformidade com PEP 695. Análise executada em 30/11/2025 confirmou zero instâncias de padrões legados.

#### Acceptance Criteria

1. WHEN a generic class is defined THEN the API_Base SHALL use PEP 695 type parameter syntax `class Name[T: Bound]` instead of `TypeVar` ✅
2. WHEN a generic function is defined THEN the API_Base SHALL use inline type parameters `def func[T]()` instead of `TypeVar` ✅
3. WHEN type aliases are needed THEN the API_Base SHALL use `type` statement instead of `TypeAlias` ✅
4. WHEN ParamSpec is needed THEN the API_Base SHALL use PEP 695 `**P` syntax for callable signatures ✅
5. WHEN scanning the codebase THEN the API_Base SHALL report zero instances of legacy `TypeVar` or `Generic[T]` patterns ✅

**Verified Components:**
- `IRepository[T, CreateT, UpdateT]` - src/my_api/shared/repository.py
- `BaseUseCase[T, CreateDTO, UpdateDTO, ResponseDTO]` - src/my_api/shared/use_case.py
- `GenericCRUDRouter[T, CreateDTO, UpdateDTO, ResponseDTO]` - src/my_api/shared/router.py
- `IMapper[Source, Target]` - src/my_api/shared/mapper.py
- `Ok[T]`, `Err[E]`, `type Result[T, E]` - src/my_api/shared/result.py
- `Specification[T]` - src/my_api/shared/specification.py
- `CircuitBreaker.call[T]` - src/my_api/shared/circuit_breaker.py
- `ApiResponse[T]`, `PaginatedResponse[T]` - src/my_api/shared/dto.py
- `SQLModelRepository[T, CreateT, UpdateT]` - src/my_api/adapters/repositories/sqlmodel_repository.py

### Requirement 2: Repository Pattern Excellence

**User Story:** As a developer, I want a fully generic repository pattern, so that I can implement data access for any entity with zero boilerplate.

#### Acceptance Criteria

1. WHEN creating a repository THEN the API_Base SHALL provide `IRepository[T, CreateT, UpdateT]` interface with all CRUD operations
2. WHEN implementing pagination THEN the API_Base SHALL return `tuple[Sequence[T], int]` with items and total count
3. WHEN soft-deleting entities THEN the API_Base SHALL set `is_deleted=True` and exclude from queries
4. WHEN filtering entities THEN the API_Base SHALL support dynamic filter dictionaries with type-safe field access
5. WHEN bulk creating entities THEN the API_Base SHALL process all items in a single transaction
6. WHEN a repository operation fails THEN the API_Base SHALL preserve the original exception chain with `from` syntax

### Requirement 3: Use Case Pattern Excellence

**User Story:** As a developer, I want generic use cases with transaction support, so that business logic is cleanly separated and testable.

#### Acceptance Criteria

1. WHEN defining a use case THEN the API_Base SHALL use `BaseUseCase[T, CreateDTO, UpdateDTO, ResponseDTO]` with PEP 695 syntax
2. WHEN getting an entity THEN the API_Base SHALL use `@overload` for type narrowing based on `raise_on_missing` parameter
3. WHEN executing multiple operations THEN the API_Base SHALL support `async with use_case.transaction()` context manager
4. WHEN validation fails THEN the API_Base SHALL raise `ValidationError` with field-level details
5. WHEN mapping entities THEN the API_Base SHALL use `IMapper[T, ResponseDTO]` interface for conversions

### Requirement 4: Router Pattern Excellence

**User Story:** As a developer, I want a generic CRUD router, so that I can expose REST endpoints for any entity with minimal configuration.

#### Acceptance Criteria

1. WHEN creating a router THEN the API_Base SHALL use `GenericCRUDRouter[T, CreateDTO, UpdateDTO, ResponseDTO]` with PEP 695 syntax
2. WHEN generating endpoints THEN the API_Base SHALL create GET, POST, PUT, DELETE with proper OpenAPI documentation
3. WHEN handling bulk operations THEN the API_Base SHALL provide `/bulk` endpoints for create and delete
4. WHEN an entity is not found THEN the API_Base SHALL return HTTP 404 with structured error response
5. WHEN pagination is requested THEN the API_Base SHALL return `PaginatedResponse[T]` with metadata

### Requirement 5: Exception Handling Excellence

**User Story:** As a developer, I want a comprehensive exception hierarchy, so that errors are handled consistently across the application.

#### Acceptance Criteria

1. WHEN an exception occurs THEN the API_Base SHALL include `correlation_id`, `timestamp`, `error_code`, `status_code`, and `details`
2. WHEN serializing exceptions THEN the API_Base SHALL preserve the cause chain in `to_dict()` output
3. WHEN validation fails THEN the API_Base SHALL normalize errors to list format `[{field, message}]`
4. WHEN using ErrorContext THEN the API_Base SHALL use `@dataclass(frozen=True, slots=True)` for memory optimization
5. WHEN chaining exceptions THEN the API_Base SHALL use `raise NewError() from original_error` syntax

### Requirement 6: Configuration Security

**User Story:** As a developer, I want secure configuration management, so that secrets are protected and validated.

#### Acceptance Criteria

1. WHEN storing secrets THEN the API_Base SHALL use `SecretStr` type that masks values in logs and repr
2. WHEN validating secret keys THEN the API_Base SHALL require minimum 32 characters (256-bit entropy)
3. WHEN logging URLs THEN the API_Base SHALL redact credentials using `redact_url_credentials()` function
4. WHEN validating rate limits THEN the API_Base SHALL enforce `number/unit` format pattern
5. WHEN using wildcard CORS in production THEN the API_Base SHALL log a security warning
6. WHEN caching settings THEN the API_Base SHALL use `@lru_cache` for singleton pattern

### Requirement 7: JWT Security (OWASP Compliant)

**User Story:** As a security engineer, I want robust JWT handling, so that authentication is secure against known attacks.

#### Acceptance Criteria

1. WHEN validating JWT algorithm THEN the API_Base SHALL reject "none" algorithm (case-insensitive)
2. WHEN verifying tokens THEN the API_Base SHALL check algorithm header matches expected before signature verification
3. WHEN creating tokens THEN the API_Base SHALL include `sub`, `exp`, `iat`, `jti`, `scopes`, `token_type` claims
4. WHEN handling refresh tokens THEN the API_Base SHALL implement replay protection with JTI tracking
5. WHEN tokens expire THEN the API_Base SHALL support configurable clock skew tolerance

### Requirement 8: Password Security (OWASP Compliant)

**User Story:** As a security engineer, I want secure password handling, so that user credentials are protected.

#### Acceptance Criteria

1. WHEN hashing passwords THEN the API_Base SHALL use Argon2id with memory 64MB, iterations 3, parallelism 4
2. WHEN validating passwords THEN the API_Base SHALL require minimum 12 characters with complexity rules
3. WHEN checking passwords THEN the API_Base SHALL reject common passwords from a 10,000+ entry list
4. WHEN comparing secrets THEN the API_Base SHALL use constant-time comparison to prevent timing attacks
5. WHEN generating salts THEN the API_Base SHALL use `secrets` module for cryptographically secure random values

### Requirement 9: HTTP Security Headers

**User Story:** As a security engineer, I want comprehensive security headers, so that the API is protected against common web attacks.

#### Acceptance Criteria

1. WHEN responding to requests THEN the API_Base SHALL include HSTS header with `max-age=31536000; includeSubDomains`
2. WHEN responding to requests THEN the API_Base SHALL include `X-Content-Type-Options: nosniff`
3. WHEN responding to requests THEN the API_Base SHALL include `X-Frame-Options: DENY`
4. WHEN responding to requests THEN the API_Base SHALL include `Referrer-Policy: strict-origin-when-cross-origin`
5. WHEN responding to requests THEN the API_Base SHALL include CSP with `default-src 'self'` and nonce-based scripts

### Requirement 10: Rate Limiting

**User Story:** As a system administrator, I want tiered rate limiting, so that the API is protected against abuse.

#### Acceptance Criteria

1. WHEN rate limit is exceeded THEN the API_Base SHALL return HTTP 429 with `Retry-After` header
2. WHEN identifying clients THEN the API_Base SHALL use IP address, API key, and user ID combination
3. WHEN applying limits THEN the API_Base SHALL support tiered limits based on authentication level
4. WHEN counting requests THEN the API_Base SHALL use sliding window algorithm for accuracy
5. WHEN violations repeat THEN the API_Base SHALL apply exponential backoff

### Requirement 11: Observability

**User Story:** As a DevOps engineer, I want comprehensive observability, so that I can monitor and debug the application.

#### Acceptance Criteria

1. WHEN logging events THEN the API_Base SHALL use structured JSON format with consistent field names
2. WHEN tracing requests THEN the API_Base SHALL propagate correlation IDs across all operations
3. WHEN configuring OpenTelemetry THEN the API_Base SHALL set service name and version attributes
4. WHEN logging health checks THEN the API_Base SHALL exclude from access logs to reduce noise
5. WHEN shutting down THEN the API_Base SHALL gracefully flush all telemetry data

### Requirement 12: Audit Logging

**User Story:** As a compliance officer, I want comprehensive audit trails, so that all security-relevant events are recorded.

#### Acceptance Criteria

1. WHEN logging audit events THEN the API_Base SHALL include timestamp, user_id, action, resource, outcome
2. WHEN logging authentication events THEN the API_Base SHALL record IP address and user agent
3. WHEN logging PII THEN the API_Base SHALL mask email, phone, SSN, and credit card patterns
4. WHEN sanitizing stack traces THEN the API_Base SHALL remove sensitive values from error details

### Requirement 13: Circuit Breaker Pattern

**User Story:** As a developer, I want circuit breaker protection, so that external service failures don't cascade.

#### Acceptance Criteria

1. WHEN failures exceed threshold THEN the API_Base SHALL open the circuit and return fallback response
2. WHEN circuit is open THEN the API_Base SHALL return HTTP 503 or configured fallback
3. WHEN testing recovery THEN the API_Base SHALL transition to half-open state after timeout
4. WHEN retrying operations THEN the API_Base SHALL use exponential backoff with jitter
5. WHEN using circuit breaker THEN the API_Base SHALL use PEP 695 syntax for generic decorators

### Requirement 14: Result Pattern

**User Story:** As a developer, I want a functional Result pattern, so that I can handle errors without exceptions.

#### Acceptance Criteria

1. WHEN returning success THEN the API_Base SHALL use `Ok[T]` with the value
2. WHEN returning failure THEN the API_Base SHALL use `Err[E]` with the error
3. WHEN transforming results THEN the API_Base SHALL provide `map()` and `map_err()` methods
4. WHEN unwrapping results THEN the API_Base SHALL provide `unwrap()` and `unwrap_or()` methods
5. WHEN using Result THEN the API_Base SHALL use `@dataclass(frozen=True, slots=True)` for immutability

### Requirement 15: Specification Pattern

**User Story:** As a developer, I want composable specifications, so that I can build complex queries declaratively.

#### Acceptance Criteria

1. WHEN combining specifications THEN the API_Base SHALL support `&` (and), `|` (or), `~` (not) operators
2. WHEN evaluating specifications THEN the API_Base SHALL use `is_satisfied_by(candidate)` method
3. WHEN using specifications THEN the API_Base SHALL use PEP 695 syntax for generic type parameters
4. WHEN converting to SQL THEN the API_Base SHALL provide `to_expression()` method for SQLAlchemy

### Requirement 16: Property-Based Testing

**User Story:** As a QA engineer, I want comprehensive property tests, so that correctness is verified across all inputs.

#### Acceptance Criteria

1. WHEN testing generics THEN the API_Base SHALL verify PEP 695 syntax compliance
2. WHEN testing repositories THEN the API_Base SHALL verify CRUD operations preserve data integrity
3. WHEN testing mappers THEN the API_Base SHALL verify round-trip consistency
4. WHEN testing exceptions THEN the API_Base SHALL verify serialization preserves all fields
5. WHEN running property tests THEN the API_Base SHALL execute minimum 100 iterations per property

### Requirement 17: Code Quality Standards

**User Story:** As a tech lead, I want enforced code quality standards, so that the codebase remains maintainable.

#### Acceptance Criteria

1. WHEN checking file sizes THEN the API_Base SHALL enforce maximum 400 lines per file
2. WHEN checking function complexity THEN the API_Base SHALL enforce maximum cyclomatic complexity of 10
3. WHEN checking nesting THEN the API_Base SHALL enforce maximum 4 levels of nesting
4. WHEN defining constants THEN the API_Base SHALL use `Final` type annotation and UPPER_SNAKE_CASE
5. WHEN exporting modules THEN the API_Base SHALL define `__all__` with explicit exports

### Requirement 18: Async Performance

**User Story:** As a performance engineer, I want optimized async operations, so that the API handles high concurrency.

#### Acceptance Criteria

1. WHEN using database connections THEN the API_Base SHALL use async session with connection pooling
2. WHEN making external calls THEN the API_Base SHALL use `httpx.AsyncClient` with connection reuse
3. WHEN running concurrent operations THEN the API_Base SHALL use `asyncio.gather()` for parallelism
4. WHEN handling timeouts THEN the API_Base SHALL use `asyncio.timeout()` context manager
5. WHEN caching results THEN the API_Base SHALL use async-compatible cache with TTL support

### Requirement 19: Documentation Standards

**User Story:** As a developer, I want comprehensive documentation, so that the API is easy to understand and use.

#### Acceptance Criteria

1. WHEN documenting functions THEN the API_Base SHALL use Google-style docstrings with Args, Returns, Raises
2. WHEN documenting classes THEN the API_Base SHALL include type parameters and usage examples
3. WHEN generating OpenAPI THEN the API_Base SHALL include descriptions for all endpoints and schemas
4. WHEN making architectural decisions THEN the API_Base SHALL document in ADR format

### Requirement 20: Zero Legacy Code (VERIFIED ✅)

**User Story:** As a maintainer, I want zero legacy or deprecated code, so that the codebase is modern and maintainable.

**Status:** Verificação executada em 30/11/2025 confirmou zero código legado.

#### Acceptance Criteria

1. WHEN scanning for TypeVar THEN the API_Base SHALL report zero instances of legacy generic syntax ✅
2. WHEN scanning for deprecated APIs THEN the API_Base SHALL report zero usage of deprecated functions ✅
3. WHEN scanning for TODO comments THEN the API_Base SHALL report zero TODOs without ticket references ✅
4. WHEN scanning for type: ignore THEN the API_Base SHALL report zero unresolved type issues ✅
5. WHEN running mypy THEN the API_Base SHALL pass with strict mode enabled

**Verified Patterns (Zero Instances Found):**
- `TypeVar` imports
- `Generic[T]` inheritance
- `TypeAlias` usage
- `from typing import Optional/Union/Dict/List/Tuple`
- `type: ignore` comments
- TODO comments without ticket references

### Requirement 21: Generic Pattern Best Practices

**User Story:** As a developer, I want consistent generic patterns across the codebase, so that code is predictable and easy to extend.

#### Acceptance Criteria

1. WHEN defining bounded generics THEN the API_Base SHALL use `T: BaseModel` syntax for Pydantic models
2. WHEN defining multiple type parameters THEN the API_Base SHALL use comma-separated syntax `[T, U, V]`
3. WHEN using generic methods THEN the API_Base SHALL define type parameters at method level `def method[T](...)`
4. WHEN creating type aliases THEN the API_Base SHALL use `type Name[T] = ...` syntax
5. WHEN implementing generic interfaces THEN the API_Base SHALL propagate type parameters to implementations
6. WHEN using dataclasses with generics THEN the API_Base SHALL combine `@dataclass(frozen=True, slots=True)` with PEP 695

### Requirement 22: Continuous Compliance Verification

**User Story:** As a tech lead, I want automated compliance checks, so that code quality is maintained over time.

#### Acceptance Criteria

1. WHEN code is committed THEN the API_Base SHALL run `scripts/analyze_pep695_compliance.py` in CI
2. WHEN new files are added THEN the API_Base SHALL verify PEP 695 compliance before merge
3. WHEN running tests THEN the API_Base SHALL include property tests for generic type correctness
4. WHEN generating reports THEN the API_Base SHALL output compliance status for all categories
5. WHEN violations are found THEN the API_Base SHALL fail the build with clear error messages

