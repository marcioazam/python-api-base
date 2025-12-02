# ADR-005: Generic Repository Pattern

## Status
Accepted

## Context

The system needs a data access abstraction that:
- Decouples domain logic from persistence details
- Supports multiple storage backends (SQL, NoSQL, in-memory)
- Provides type safety with Python generics (PEP 695)
- Enables easy testing with mock implementations

## Decision

We implement a protocol-based generic repository pattern:

### Protocol Definition

```python
# src/core/protocols/repository.py
class AsyncRepository[T, ID](Protocol):
    """Generic async repository protocol."""

    async def get(self, id: ID) -> T | None:
        """Get entity by ID."""
        ...

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[T]:
        """Get all entities with pagination."""
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

### SQLAlchemy Implementation

```python
# src/infrastructure/db/repositories/
class SQLAlchemyRepository[T: SQLModel, ID](AsyncRepository[T, ID]):
    def __init__(self, session: AsyncSession, model: type[T]):
        self._session = session
        self._model = model

    async def get(self, id: ID) -> T | None:
        return await self._session.get(self._model, id)

    async def create(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity
```

### In-Memory Implementation (Testing)

```python
# src/infrastructure/db/repositories/
class InMemoryRepository[T, ID](AsyncRepository[T, ID]):
    def __init__(self):
        self._store: dict[ID, T] = {}

    async def get(self, id: ID) -> T | None:
        return self._store.get(id)
```

### Domain Repository Interface

```python
# src/domain/users/repositories.py
class IUserRepository(AsyncRepository[User, str], Protocol):
    """User-specific repository interface."""

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        ...
```

## Consequences

### Positive
- Clean separation between domain and infrastructure
- Type-safe with full IDE support
- Easy to swap implementations
- Testable with in-memory implementations

### Negative
- Additional abstraction layer
- Some queries may not fit repository pattern
- Learning curve for team members

### Neutral
- Requires discipline to keep repositories focused
- Complex queries may need query builder

## Alternatives Considered

1. **Active Record pattern** - Rejected as couples domain to persistence
2. **Direct ORM usage** - Rejected as makes testing difficult
3. **CQRS-only (no repository)** - Rejected as too complex for simple operations

## References

- [src/core/protocols/](../../src/core/protocols/)
- [src/infrastructure/db/repositories/](../../src/infrastructure/db/repositories/)
- [src/domain/users/repositories.py](../../src/domain/users/repositories.py)

## History

| Date | Status | Notes |
|------|--------|-------|
| 2024-12-02 | Proposed | Initial proposal |
| 2024-12-02 | Accepted | Approved for implementation |
