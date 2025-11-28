# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Property-based tests for Circuit Breaker state transitions
- Property-based tests for Rate Limiter response format
- Load testing configuration with k6
- ADR-005: Large file refactoring documentation

### Changed
- Updated architecture documentation with conformance status
- Refactored `query_builder.py` (562 lines) into `query_builder/` package
- Refactored `batch.py` (581 lines) into `batch/` package

### Fixed
- **Security**: Added IP validation in rate limiter to prevent X-Forwarded-For header spoofing
- Backward compatibility maintained via re-exports in refactored modules

## [0.1.0] - 2024-11-27

### Added

#### Core Framework
- Generic CRUD operations with `IRepository[T]`, `BaseUseCase[T]`, `GenericCRUDRouter[T]`
- Clean Architecture structure with domain, application, adapters, and infrastructure layers
- Dependency injection with `dependency-injector`
- Pydantic v2 for validation and serialization
- SQLModel for ORM with async support

#### Authentication & Authorization
- JWT authentication with access/refresh token pairs
- Token revocation with Redis-backed blacklist
- Role-Based Access Control (RBAC) with permission composition
- Password hashing with Argon2
- Password policy enforcement

#### Security
- Security headers middleware (CSP, HSTS, X-Frame-Options, etc.)
- Rate limiting with slowapi
- CORS configuration
- Input validation and sanitization
- RFC 7807 Problem Details for error responses

#### Observability
- Structured logging with structlog (JSON format)
- Distributed tracing with OpenTelemetry
- Metrics collection with OpenTelemetry MeterProvider
- Request ID middleware for tracing
- Health check endpoints (`/health/live`, `/health/ready`)
- PII redaction in logs

#### Resilience Patterns
- Circuit breaker for external service calls
- Retry with exponential backoff and jitter
- Multi-level caching (in-memory + Redis)
- Connection pooling for database

#### API Design
- URL path versioning (`/api/v1/`)
- RFC 8594 deprecation headers
- Paginated responses with navigation metadata
- Bulk operations (create/delete)

#### Developer Experience
- Code generation script (`scripts/generate_entity.py`)
- Configuration documentation generator
- Pre-commit hooks for code quality
- Type checking with mypy (strict mode)
- Linting and formatting with ruff

#### Testing
- 148+ tests (unit, integration, property-based)
- Property-based testing with Hypothesis
- Test fixtures and factories
- Coverage reporting

#### Documentation
- Architecture documentation with Mermaid diagrams
- ADRs for significant decisions (JWT, RBAC, Versioning, Token Revocation)
- OpenAPI documentation (Swagger UI, ReDoc)
- README with quick start guide

### Security
- Minimum 32-character secret key requirement
- Short-lived access tokens (30 minutes)
- Long-lived refresh tokens (7 days) with revocation support
- OWASP API Security Top 10 compliance

[Unreleased]: https://github.com/example/my-api/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/example/my-api/releases/tag/v0.1.0
