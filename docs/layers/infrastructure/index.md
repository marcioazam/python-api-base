# Infrastructure Layer

## Overview

A **Infrastructure Layer** contém implementações concretas de interfaces definidas no domínio, incluindo acesso a banco de dados, cache, messaging, storage e integrações externas.

## Directory Structure

```
src/infrastructure/
├── __init__.py
├── exceptions.py            # Infrastructure exceptions
├── audit/                   # Audit trail
├── auth/                    # Authentication (JWT, Password)
├── cache/                   # Cache (Redis, Memory)
├── db/                      # Database (SQLAlchemy)
├── elasticsearch/           # Search engine
├── kafka/                   # Event streaming
├── minio/                   # Object storage
├── observability/           # Telemetry, Logging
├── rbac/                    # Role-Based Access Control
├── redis/                   # Redis client
├── resilience/              # Circuit Breaker, Retry, Bulkhead
├── storage/                 # File storage abstraction
└── tasks/                   # Background tasks (RabbitMQ)
```

## Key Components

| Component | Documentation |
|-----------|---------------|
| Database | [database.md](database.md) |
| Cache | [cache.md](cache.md) |
| Messaging | [messaging.md](messaging.md) |
| Storage | [storage.md](storage.md) |
| Resilience | [resilience.md](resilience.md) |

## Dependency Rules

### Allowed Imports ✅
```python
# Domain layer (interfaces)
from domain.users.repository import IUserRepository
from domain.users.entities import User

# Core layer
from core.config import get_settings
from core.protocols import AsyncRepository

# External libraries
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
```

### Prohibited Imports ❌
```python
# Application layer
from application.users.dtos import UserDTO  # ❌

# Interface layer
from fastapi import APIRouter  # ❌
```

## Patterns Used

| Pattern | Location | Purpose |
|---------|----------|---------|
| Repository | `db/repositories/` | Data access abstraction |
| Unit of Work | `db/unit_of_work.py` | Transaction management |
| Circuit Breaker | `resilience/` | Fault tolerance |
| Retry | `resilience/` | Transient failure handling |
| Provider | `cache/`, `storage/` | Pluggable implementations |

## Exception Hierarchy

```python
InfrastructureError           # Base
├── DatabaseError             # Database errors
│   └── ConnectionPoolError   # Pool exhausted
├── CacheError                # Cache errors
├── MessagingError            # Kafka/RabbitMQ errors
├── StorageError              # MinIO/S3 errors
└── ExternalServiceError      # External API errors
```

## Testing Guidelines

- Use in-memory implementations for unit tests
- Use testcontainers for integration tests
- Mock external services
- Test error handling and retries
