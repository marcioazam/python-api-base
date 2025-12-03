# Repository Interfaces

## Overview

Repository interfaces define contracts for data access, abstracting persistence details from the domain layer.

## Repository Protocol

```python
from typing import Protocol, Generic, TypeVar

TEntity = TypeVar("TEntity")
TId = TypeVar("TId")

class IRepository(Protocol, Generic[TEntity, TId]):
    """Base repository interface."""
    
    async def get(self, id: TId) -> TEntity | None:
        """Get entity by ID."""
        ...
    
    async def get_all(self) -> list[TEntity]:
        """Get all entities."""
        ...
    
    async def add(self, entity: TEntity) -> TEntity:
        """Add new entity."""
        ...
    
    async def update(self, entity: TEntity) -> TEntity:
        """Update existing entity."""
        ...
    
    async def delete(self, id: TId) -> bool:
        """Delete entity by ID."""
        ...
    
    async def exists(self, id: TId) -> bool:
        """Check if entity exists."""
        ...
```

## Extended Repository

```python
class IQueryableRepository(IRepository[TEntity, TId], Protocol):
    """Repository with query capabilities."""
    
    async def find(
        self,
        specification: Specification[TEntity],
    ) -> list[TEntity]:
        """Find entities matching specification."""
        ...
    
    async def find_one(
        self,
        specification: Specification[TEntity],
    ) -> TEntity | None:
        """Find single entity matching specification."""
        ...
    
    async def count(
        self,
        specification: Specification[TEntity] | None = None,
    ) -> int:
        """Count entities matching specification."""
        ...
    
    async def find_paginated(
        self,
        specification: Specification[TEntity] | None,
        pagination: PaginationParams,
        sort: SortParams | None = None,
    ) -> PaginatedResult[TEntity]:
        """Find entities with pagination."""
        ...
```

## User Repository

```python
class IUserRepository(IQueryableRepository[User, ULID], Protocol):
    """User repository interface."""
    
    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        ...
    
    async def get_active_users(self) -> list[User]:
        """Get all active users."""
        ...
    
    async def get_by_role(self, role: str) -> list[User]:
        """Get users by role."""
        ...
```

## Item Repository

```python
class IItemRepository(IQueryableRepository[Item, ULID], Protocol):
    """Item repository interface."""
    
    async def get_by_owner(self, owner_id: ULID) -> list[Item]:
        """Get items by owner."""
        ...
    
    async def get_available_items(self) -> list[Item]:
        """Get items with quantity > 0."""
        ...
    
    async def search(
        self,
        query: str,
        pagination: PaginationParams,
    ) -> PaginatedResult[Item]:
        """Search items by name/description."""
        ...
```

## Repository Contract

### CRUD Operations

| Method | Description | Returns |
|--------|-------------|---------|
| `get(id)` | Get by ID | Entity or None |
| `get_all()` | Get all entities | List of entities |
| `add(entity)` | Create new entity | Created entity |
| `update(entity)` | Update existing | Updated entity |
| `delete(id)` | Delete by ID | Success boolean |
| `exists(id)` | Check existence | Boolean |

### Query Operations

| Method | Description | Returns |
|--------|-------------|---------|
| `find(spec)` | Find by specification | List of entities |
| `find_one(spec)` | Find single match | Entity or None |
| `count(spec)` | Count matches | Integer |
| `find_paginated(...)` | Paginated query | PaginatedResult |

## Usage in Domain

```python
# Domain service using repository interface
class UserDomainService:
    def __init__(self, repository: IUserRepository):
        self._repository = repository
    
    async def get_active_admins(self) -> list[User]:
        active_spec = FieldSpecification("is_active", ComparisonOperator.EQ, True)
        admin_spec = FieldSpecification("role", ComparisonOperator.EQ, "admin")
        
        return await self._repository.find(
            active_spec.and_spec(admin_spec)
        )
```

## Implementation Location

Repository implementations are in the Infrastructure layer:

```
src/infrastructure/db/repositories/
├── __init__.py
├── base.py           # Base SQLAlchemy repository
├── user_repository.py
└── item_repository.py
```

## Related Documentation

- [Specifications](specifications.md)
- [Database Infrastructure](../infrastructure/database.md)
- [Protocols](../core/protocols.md)
