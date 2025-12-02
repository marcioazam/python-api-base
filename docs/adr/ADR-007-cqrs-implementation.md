# ADR-007: CQRS Implementation

## Status
Accepted

## Context

The system needs to:
- Separate read and write operations for clarity
- Enable different optimization strategies for reads vs writes
- Support command validation and authorization
- Enable caching of query results

## Decision

We implement Command Query Responsibility Segregation (CQRS):

### Command Structure

```python
# src/application/common/cqrs/handlers.py
@dataclass
class Command[TResult](ABC):
    """Base class for commands (write operations)."""

    @abstractmethod
    async def execute(self) -> Result[TResult, str]:
        """Execute the command."""
        ...

# Example: src/application/users/commands/create_user.py
@dataclass
class CreateUserCommand(Command[User]):
    email: str
    name: str
    password: str

    async def execute(self, repository: IUserRepository) -> Result[User, str]:
        if await repository.exists_by_email(self.email):
            return Err("Email already exists")

        user = User(
            id=generate_ulid(),
            email=self.email,
            name=self.name,
            password_hash=hash_password(self.password),
        )
        return Ok(await repository.create(user))
```

### Query Structure

```python
# src/application/common/cqrs/handlers.py
@dataclass
class Query[TResult](ABC):
    """Base class for queries (read operations)."""

    cacheable: bool = False
    cache_ttl: int = 300

    @abstractmethod
    async def execute(self) -> TResult:
        """Execute the query."""
        ...

# Example: src/application/users/queries/get_user.py
@dataclass
class GetUserQuery(Query[UserDTO | None]):
    user_id: str
    cacheable: bool = True

    async def execute(self, repository: IUserRepository) -> UserDTO | None:
        user = await repository.get(self.user_id)
        return UserMapper.to_dto(user) if user else None
```

### Handler Pattern

```python
# src/application/common/cqrs/handlers.py
class CommandHandler[TCommand: Command, TResult](Protocol):
    async def handle(self, command: TCommand) -> Result[TResult, str]:
        ...

class QueryHandler[TQuery: Query, TResult](Protocol):
    async def handle(self, query: TQuery) -> TResult:
        ...
```

### Bus Implementation

```python
# src/application/common/cqrs/bus.py
class CommandBus:
    async def dispatch[T](self, command: Command[T]) -> Result[T, str]:
        handler = self._get_handler(type(command))
        return await handler.handle(command)

class QueryBus:
    async def dispatch[T](self, query: Query[T]) -> T:
        handler = self._get_handler(type(query))
        if query.cacheable:
            return await self._cached_execute(query, handler)
        return await handler.handle(query)
```

## Consequences

### Positive
- Clear separation of concerns
- Optimized read/write paths
- Easy to add caching to queries
- Commands are self-documenting

### Negative
- More classes to maintain
- Overhead for simple operations
- Learning curve for team

### Neutral
- Can evolve to event sourcing later
- Works well with DDD patterns

## Alternatives Considered

1. **Service layer only** - Rejected as mixes read/write concerns
2. **Full event sourcing** - Rejected as too complex for current needs
3. **Repository-only** - Rejected as doesn't support query optimization

## References

- [src/application/common/cqrs/](../../src/application/common/cqrs/)
- [src/application/users/commands/](../../src/application/users/commands/)
- [src/application/users/queries/](../../src/application/users/queries/)

## History

| Date | Status | Notes |
|------|--------|-------|
| 2024-12-02 | Proposed | Initial proposal |
| 2024-12-02 | Accepted | Approved for implementation |
