# ADR-012: Clean Architecture Layers

## Status
Accepted

## Context

The system needs an architecture that:
- Separates concerns clearly
- Enables independent testing of components
- Allows technology changes without domain impact
- Supports long-term maintainability

## Decision

We implement Clean Architecture with 5 layers:

### Layer Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERFACE LAYER                          │
│  (FastAPI Routers, Middleware, GraphQL, WebSocket, Versioning)  │
├─────────────────────────────────────────────────────────────────┤
│                       APPLICATION LAYER                         │
│    (Use Cases, Commands, Queries, DTOs, Mappers, Services)      │
├─────────────────────────────────────────────────────────────────┤
│                         DOMAIN LAYER                            │
│   (Entities, Value Objects, Aggregates, Specifications, Events) │
├─────────────────────────────────────────────────────────────────┤
│                      INFRASTRUCTURE LAYER                       │
│  (Database, Cache, Messaging, Storage, Auth, Observability)     │
├─────────────────────────────────────────────────────────────────┤
│                          CORE LAYER                             │
│     (Configuration, DI Container, Protocols, Base Types)        │
└─────────────────────────────────────────────────────────────────┘
```

### Dependency Rule

```
Interface → Application → Domain ← Infrastructure
                ↓
              Core
```

**Rule:** Dependencies point inward. Outer layers depend on inner layers, never the reverse.

### Layer Responsibilities

| Layer | Responsibility | Examples |
|-------|---------------|----------|
| Core | Shared infrastructure | Config, Protocols, DI |
| Domain | Business logic | Entities, Specifications |
| Application | Use case orchestration | Commands, Queries, DTOs |
| Infrastructure | External integrations | Database, Cache, APIs |
| Interface | API exposure | REST, GraphQL, WebSocket |

### Import Rules

**Allowed:**
```python
# Interface → Application
from application.users.dtos import UserDTO

# Application → Domain
from domain.users.entities import User

# Infrastructure → Domain
from domain.users.repository import IUserRepository

# All → Core
from core.protocols import AsyncRepository
```

**Forbidden:**
```python
# Domain → Application ❌
from application.users.dtos import UserDTO

# Domain → Infrastructure ❌
from infrastructure.db.session import get_session

# Application → Interface ❌
from interface.v1.users import router
```

### Directory Structure

```
src/
├── core/           # Kernel - no dependencies
│   ├── config/
│   ├── protocols/
│   ├── errors/
│   └── types/
├── domain/         # Business logic - depends on core
│   ├── common/
│   ├── users/
│   └── items/
├── application/    # Use cases - depends on domain, core
│   ├── common/
│   ├── users/
│   └── items/
├── infrastructure/ # External - depends on domain, core
│   ├── db/
│   ├── cache/
│   └── auth/
└── interface/      # API - depends on application, infrastructure
    ├── v1/
    └── middleware/
```

## Consequences

### Positive
- Clear separation of concerns
- Domain isolated from infrastructure
- Easy to test each layer
- Technology changes don't affect domain

### Negative
- More files and directories
- Learning curve for team
- Some boilerplate code

### Neutral
- Requires discipline to maintain boundaries
- IDE support helps enforce rules

## Alternatives Considered

1. **Layered architecture (traditional)** - Rejected as allows upward dependencies
2. **Hexagonal architecture** - Similar; Clean Architecture chosen for clearer terminology
3. **Microservices** - Rejected as premature; can evolve to this later

## References

- [src/core/](../../src/core/)
- [src/domain/](../../src/domain/)
- [src/application/](../../src/application/)
- [src/infrastructure/](../../src/infrastructure/)
- [src/interface/](../../src/interface/)
- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

## History

| Date | Status | Notes |
|------|--------|-------|
| 2024-12-02 | Proposed | Initial proposal |
| 2024-12-02 | Accepted | Approved for implementation |
