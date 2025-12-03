# Application Layer

## Overview

A **Application Layer** orquestra casos de uso, coordenando entre domínio e infraestrutura. Implementa CQRS (Command Query Responsibility Segregation) para separar operações de leitura e escrita.

## Directory Structure

```
src/application/
├── __init__.py
├── common/                  # Infraestrutura compartilhada
│   ├── __init__.py
│   ├── cqrs/               # Command/Query Separation
│   │   ├── __init__.py
│   │   ├── commands.py     # Command base
│   │   ├── queries.py      # Query base
│   │   └── bus.py          # CommandBus, QueryBus
│   ├── middleware/         # Pipeline middleware
│   │   ├── __init__.py
│   │   └── pipeline.py
│   ├── batch/              # Batch operations
│   │   └── __init__.py
│   ├── dtos.py             # DTOs base
│   ├── mappers.py          # Mapper base
│   └── exceptions.py       # Application exceptions
├── services/                # Cross-cutting services
│   ├── __init__.py
│   ├── feature_flags/
│   ├── file_upload/
│   └── multitenancy/
├── users/                   # Users bounded context
│   ├── __init__.py
│   ├── commands/
│   ├── queries/
│   ├── dtos.py
│   └── mappers.py
└── items/                   # Items bounded context
    ├── __init__.py
    ├── commands/
    ├── queries/
    ├── dtos.py
    └── mappers.py
```

## Key Components

### CQRS
Separação de comandos (escrita) e queries (leitura).
[Detalhes →](cqrs.md)

### Use Cases
Orquestração de operações de negócio.
[Detalhes →](use-cases.md)

### DTOs & Mappers
Objetos de transferência e conversão entre camadas.
[Detalhes →](dtos-mappers.md)

### Services
Serviços cross-cutting como feature flags e multitenancy.
[Detalhes →](services.md)

## Dependency Rules

### Allowed Imports ✅
```python
# Domain layer
from domain.users.entities import User
from domain.users.repository import IUserRepository
from domain.common.specification import Specification

# Core layer
from core.protocols import Command, Query
from core.config import get_settings
```

### Prohibited Imports ❌
```python
# Infrastructure implementations
from infrastructure.db.repositories import UserRepository  # ❌
from sqlalchemy import select  # ❌

# Interface layer
from fastapi import APIRouter  # ❌
from interface.v1.users import router  # ❌
```

## Patterns Used

| Pattern | Location | Purpose |
|---------|----------|---------|
| CQRS | `common/cqrs/` | Separate read/write |
| DTO | `*/dtos.py` | Data transfer |
| Mapper | `*/mappers.py` | Entity ↔ DTO conversion |
| Use Case | `*/commands/`, `*/queries/` | Business orchestration |
| Middleware | `common/middleware/` | Cross-cutting concerns |

## Code Examples

### Command
```python
@dataclass
class CreateUserCommand(Command[User]):
    email: str
    name: str
    password: str
    
    async def execute(self, repository: IUserRepository) -> Result[User, str]:
        if await repository.exists_by_email(self.email):
            return Err("Email already exists")
        user = User.create(self.email, self.name, self.password)
        return Ok(await repository.create(user))
```

### Query
```python
@dataclass
class GetUserQuery(Query[UserDTO | None]):
    user_id: str
    
    async def execute(self, repository: IUserRepository) -> UserDTO | None:
        user = await repository.get(self.user_id)
        return UserMapper.to_dto(user) if user else None
```

## Testing Guidelines

- Mock repository interfaces, not implementations
- Test command validation logic
- Test query caching behavior
- Use Result pattern for error handling

## Common Mistakes

| Mistake | Solution |
|---------|----------|
| Importing infrastructure | Use interfaces from domain |
| Business logic in commands | Move to domain entities |
| Direct database access | Use repository interfaces |
| Returning entities to interface | Return DTOs |
