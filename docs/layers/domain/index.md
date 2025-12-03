# Domain Layer

## Overview

A **Domain Layer** contém a lógica de negócio pura do sistema, incluindo entidades, value objects, aggregates, specifications e domain events. Esta camada não possui dependências de frameworks ou infraestrutura.

## Directory Structure

```
src/domain/
├── __init__.py
├── common/                  # Componentes compartilhados
│   ├── __init__.py
│   ├── specification.py    # Specification Pattern
│   ├── value_objects.py    # Value Objects base
│   ├── events.py           # Domain Events base
│   └── aggregates.py       # Aggregate Root base
├── users/                   # Bounded Context: Users
│   ├── __init__.py
│   ├── entities.py         # User entity
│   ├── repository.py       # IUserRepository (interface)
│   ├── value_objects.py    # Email, Password, etc.
│   ├── events.py           # UserCreated, UserUpdated
│   └── specifications.py   # User specifications
├── items/                   # Bounded Context: Items
│   ├── __init__.py
│   ├── entities.py
│   ├── repository.py
│   └── events.py
└── examples/                # Bounded Context: Examples
    ├── __init__.py
    ├── entities.py
    └── repository.py
```

## Key Components

### Entities
Objetos com identidade única que persistem ao longo do tempo.
[Detalhes →](entities.md)

### Value Objects
Objetos imutáveis definidos por seus atributos, sem identidade.
[Detalhes →](value-objects.md)

### Specifications
Regras de negócio encapsuladas em objetos composáveis.
[Detalhes →](specifications.md)

### Domain Events
Eventos que representam mudanças significativas no domínio.
[Detalhes →](domain-events.md)

## Dependency Rules

### Allowed Imports ✅
```python
# Standard library
from typing import Protocol
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

# Core layer (protocols only)
from core.protocols import Entity, TrackedEntity
```

### Prohibited Imports ❌
```python
# Application layer
from application.users.dtos import UserDTO  # ❌

# Infrastructure layer
from infrastructure.db.session import get_session  # ❌
from sqlalchemy import Column  # ❌

# Interface layer
from fastapi import APIRouter  # ❌

# External services
import redis  # ❌
```

## Patterns Used

| Pattern | Location | Purpose |
|---------|----------|---------|
| Entity | `*/entities.py` | Objects with identity |
| Value Object | `*/value_objects.py` | Immutable objects |
| Specification | `common/specification.py` | Composable business rules |
| Repository Interface | `*/repository.py` | Data access abstraction |
| Domain Event | `*/events.py` | State change notifications |
| Aggregate Root | `common/aggregates.py` | Consistency boundary |

## Code Examples

### Entity Definition
```python
from dataclasses import dataclass, field
from datetime import datetime
from ulid import ULID

@dataclass
class User:
    id: str = field(default_factory=lambda: str(ULID()))
    email: str
    name: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
```

### Repository Interface
```python
from typing import Protocol

class IUserRepository(Protocol):
    async def get(self, id: str) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def create(self, user: User) -> User: ...
    async def update(self, user: User) -> User: ...
    async def delete(self, id: str) -> bool: ...
```

## Testing Guidelines

- Test entities in isolation without mocks
- Test value object validation and equality
- Test specification composition logic
- Use property-based testing for invariants

## Common Mistakes

| Mistake | Solution |
|---------|----------|
| Using ORM models as entities | Create pure domain entities |
| Importing infrastructure | Define interfaces in domain |
| Mutable value objects | Use frozen dataclasses |
| Business logic in services | Move to entities/specifications |
