# Core Layer

## Overview

A **Core Layer** é o kernel da aplicação, contendo configurações, protocolos (interfaces), container de injeção de dependência e utilitários fundamentais. Esta camada não possui dependências de outras camadas do sistema.

## Directory Structure

```
src/core/
├── __init__.py
├── base/                    # Classes base abstratas
│   ├── __init__.py
│   ├── entity.py           # BaseEntity
│   └── repository.py       # BaseRepository
├── config/                  # Configurações centralizadas
│   ├── __init__.py
│   ├── settings.py         # Settings principal
│   ├── database.py         # DatabaseSettings
│   ├── security.py         # SecuritySettings
│   ├── observability.py    # ObservabilitySettings
│   └── utils.py            # Utilitários de config
├── di/                      # Dependency Injection
│   ├── __init__.py
│   └── container.py        # DI Container
├── errors/                  # Exception handling
│   ├── __init__.py
│   ├── handlers.py         # FastAPI handlers
│   └── exceptions.py       # Base exceptions
├── protocols/               # Interfaces (Protocol classes)
│   ├── __init__.py
│   ├── base.py             # Identifiable, Timestamped
│   ├── entities.py         # Entity protocols
│   └── repository.py       # Repository protocols
├── shared/                  # Utilitários compartilhados
│   ├── __init__.py
│   ├── logging.py          # Structured logging
│   └── utils.py            # Funções utilitárias
└── types/                   # Type definitions
    ├── __init__.py
    └── common.py           # Type aliases
```

## Key Components

### Configuration System
Sistema de configuração baseado em Pydantic Settings com validação automática.
[Detalhes →](configuration.md)

### Protocols (Interfaces)
Definição de contratos usando Python Protocol classes (PEP 544).
[Detalhes →](protocols.md)

### Dependency Injection
Container de DI usando dependency-injector para IoC.
[Detalhes →](dependency-injection.md)

### Error Handling
Sistema de tratamento de erros seguindo RFC 7807 (Problem Details).
[Detalhes →](error-handling.md)

## Dependency Rules

### Allowed Imports ✅
```python
# Standard library
from typing import Protocol, TypeVar, Generic
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Third-party (core dependencies only)
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import structlog
```

### Prohibited Imports ❌
```python
# Domain layer
from domain.users.entities import User  # ❌

# Application layer
from application.users.dtos import UserDTO  # ❌

# Infrastructure layer
from infrastructure.db.session import get_session  # ❌

# Interface layer
from interface.v1.users import router  # ❌
```

## Patterns Used

| Pattern | Location | Purpose |
|---------|----------|---------|
| Protocol | `protocols/` | Define interfaces without inheritance |
| Singleton | `config/settings.py` | Single configuration instance |
| Factory | `di/container.py` | Create dependencies |

## Code Examples

### Settings Usage
```python
from core.config import get_settings

settings = get_settings()
print(settings.database.url)
print(settings.security.secret_key)
```

### Protocol Definition
```python
from typing import Protocol

class AsyncRepository[T, ID](Protocol):
    async def get(self, id: ID) -> T | None: ...
    async def create(self, entity: T) -> T: ...
```

## Testing Guidelines

- Unit test configuration loading with different env values
- Test protocol implementations satisfy contracts
- Mock external dependencies in DI container tests

## Common Mistakes

| Mistake | Solution |
|---------|----------|
| Importing domain entities | Use protocols instead |
| Hardcoding configuration | Use Settings classes |
| Not using type hints | Always use PEP 695 generics |
