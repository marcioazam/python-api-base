# Protocols (Interfaces)

## Overview

O sistema utiliza Python Protocol classes (PEP 544) para definir interfaces sem herança, permitindo duck typing estrutural com verificação de tipos estática.

## Base Protocols

### Identifiable

```python
from typing import Protocol

class Identifiable(Protocol):
    """Entity with unique identifier."""
    id: str
```

### Timestamped

```python
class Timestamped(Protocol):
    """Entity with creation and update timestamps."""
    created_at: datetime
    updated_at: datetime | None
```

### SoftDeletable

```python
class SoftDeletable(Protocol):
    """Entity with soft delete support."""
    deleted_at: datetime | None
    
    @property
    def is_deleted(self) -> bool: ...
```

## Entity Protocols

### Entity

```python
class Entity(Identifiable, Protocol):
    """Base entity protocol."""
    pass
```

### TrackedEntity

```python
class TrackedEntity(Entity, Timestamped, Protocol):
    """Entity with timestamps."""
    pass
```

### VersionedEntity

```python
class VersionedEntity(TrackedEntity, Protocol):
    """Entity with optimistic locking."""
    version: int
```

### FullEntity

```python
class FullEntity(VersionedEntity, SoftDeletable, Protocol):
    """Entity with all features."""
    pass
```

## Repository Protocol

```python
class AsyncRepository[T, ID](Protocol):
    """Generic async repository interface."""
    
    async def get(self, id: ID) -> T | None:
        """Get entity by ID."""
        ...
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[T]:
        """List entities with pagination."""
        ...
    
    async def create(self, entity: T) -> T:
        """Create new entity."""
        ...
    
    async def update(self, entity: T) -> T:
        """Update existing entity."""
        ...
    
    async def delete(self, id: ID) -> bool:
        """Delete entity by ID."""
        ...
    
    async def exists(self, id: ID) -> bool:
        """Check if entity exists."""
        ...
```

## CQRS Protocols

### Command

```python
class Command[TResult](Protocol):
    """Command for write operations."""
    
    async def execute(self, *args, **kwargs) -> TResult:
        ...
```

### Query

```python
class Query[TResult](Protocol):
    """Query for read operations."""
    cacheable: bool
    cache_ttl: int
    
    async def execute(self, *args, **kwargs) -> TResult:
        ...
```

## Cache Protocol

```python
class CacheProvider[T](Protocol):
    """Cache provider interface."""
    
    async def get(self, key: str) -> T | None: ...
    async def set(self, key: str, value: T, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> bool: ...
    async def exists(self, key: str) -> bool: ...
    async def clear_pattern(self, pattern: str) -> int: ...
```

## Usage Example

```python
# Define domain repository extending base protocol
class IUserRepository(AsyncRepository[User, str], Protocol):
    async def get_by_email(self, email: str) -> User | None: ...
    async def exists_by_email(self, email: str) -> bool: ...

# Implementation satisfies protocol without inheritance
class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get(self, id: str) -> User | None:
        return await self._session.get(User, id)
    
    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    # ... other methods
```

## Type Checking

```python
# mypy verifies protocol compliance
def process_user(repo: IUserRepository) -> None:
    user = await repo.get("123")  # OK
    user = await repo.get_by_email("test@example.com")  # OK

# Passing non-compliant object raises type error
class BadRepo:
    pass

process_user(BadRepo())  # mypy error: incompatible type
```
