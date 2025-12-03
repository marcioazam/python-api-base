# Architecture Decisions Summary

## Overview

Summary of key architectural decisions documented in ADRs.

## Decisions

| ADR | Title | Status | Impact |
|-----|-------|--------|--------|
| [ADR-001](../adr/ADR-001-jwt-authentication.md) | JWT Authentication | Accepted | High |
| [ADR-002](../adr/ADR-002-rbac-implementation.md) | RBAC Implementation | Accepted | High |
| [ADR-003](../adr/ADR-003-api-versioning.md) | API Versioning | Accepted | Medium |
| [ADR-004](../adr/ADR-004-token-revocation.md) | Token Revocation | Accepted | Medium |
| [ADR-005](../adr/ADR-005-repository-pattern.md) | Repository Pattern | Accepted | High |
| [ADR-006](../adr/ADR-006-specification-pattern.md) | Specification Pattern | Accepted | Medium |
| [ADR-007](../adr/ADR-007-cqrs-implementation.md) | CQRS Implementation | Accepted | High |
| [ADR-008](../adr/ADR-008-cache-strategy.md) | Cache Strategy | Accepted | Medium |
| [ADR-009](../adr/ADR-009-resilience-patterns.md) | Resilience Patterns | Accepted | High |
| [ADR-010](../adr/ADR-010-error-handling.md) | Error Handling | Accepted | Medium |
| [ADR-011](../adr/ADR-011-observability-stack.md) | Observability Stack | Accepted | Medium |
| [ADR-012](../adr/ADR-012-clean-architecture.md) | Clean Architecture | Accepted | High |

## Key Decisions

### Authentication (ADR-001)

- JWT with access/refresh tokens
- Short-lived access tokens (30 min)
- Redis-based token revocation

### Architecture (ADR-012)

- Clean Architecture with 5 layers
- Dependency rule: inward only
- Protocol-based interfaces

### Data Access (ADR-005, ADR-006)

- Generic repository pattern
- Specification pattern for queries
- CQRS for read/write separation

### Resilience (ADR-009)

- Circuit breaker for external calls
- Retry with exponential backoff
- Bulkhead for isolation

## Related

- [C4 Model](c4-model.md)
- [Data Flows](data-flows.md)
- [ADR Directory](../adr/)
