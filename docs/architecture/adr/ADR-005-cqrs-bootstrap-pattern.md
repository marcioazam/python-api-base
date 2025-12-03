# ADR-005: CQRS Bootstrap Pattern

**Status:** Accepted

**Date:** 2025-01-02

**Deciders:** Architecture Team

**Technical Story:** Document the factory pattern used for registering CQRS handlers with fresh repository instances per request.

---

## Context

The CQRS pattern requires registering command and query handlers to their respective buses. The challenge is how to provide handlers with their dependencies (repositories, services) while ensuring proper lifecycle management (fresh database sessions per request).

### Initial Approaches Considered

**Option 1: Singleton Handlers with Shared Dependencies**
```python
# ❌ PROBLEMATIC
repo = SQLAlchemyUserRepository(global_session)  # Shared session!
handler = CreateUserHandler(repo, service)
command_bus.register(CreateUserCommand, handler.handle)
```

**Problems:**
- Shared database session across requests
- Thread safety issues
- Connection pool exhaustion
- Stale data from cached sessions

**Option 2: Handler Instances Per Request**
```python
# ❌ COMPLEX
@router.post("/users")
async def create_user(data: CreateUserDTO):
    async with db.session() as session:
        repo = SQLAlchemyUserRepository(session)
        handler = CreateUserHandler(repo, service)
        result = await handler.handle(CreateUserCommand(...))
```

**Problems:**
- Router knows about repositories and handlers
- Violates single responsibility
- Duplicated session management code
- Tight coupling

## Decision

**We use the Factory Pattern for handler registration**, where each handler is registered with a factory function that creates fresh dependencies per invocation.

### Implementation Pattern

Located in `src/infrastructure/di/cqrs_bootstrap.py`:

```python
async def register_user_handlers(command_bus: CommandBus, query_bus: QueryBus):
    """Register all user-related handlers."""

    # Create shared stateless services (singleton-safe)
    user_service = UserDomainService()

    # Register command handlers with factory pattern
    async def create_user_handler(cmd: CreateUserCommand):
        """Factory creates fresh repository per invocation."""
        db = get_database_session()  # Get session manager
        async with db.session() as session:  # Fresh session per request
            repo = SQLAlchemyUserRepository(session)  # Fresh repo
            handler = CreateUserHandler(
                user_repository=repo,
                user_service=user_service,  # Shared stateless service
            )
            return await handler.handle(cmd)

    command_bus.register(CreateUserCommand, create_user_handler)

    # Similar pattern for queries
    async def get_user_handler(query: GetUserByIdQuery):
        db = get_database_session()
        async with db.session() as session:
            repo = SQLAlchemyUserRepository(session)
            handler = GetUserByIdHandler(repository=repo)
            return await handler.handle(query)

    query_bus.register(GetUserByIdQuery, get_user_handler)
```

### Bootstrap Flow

```
Application Startup (main.py:70-76)
    ↓
Create DI Container
    ↓
Get CommandBus and QueryBus (singletons)
    ↓
Call bootstrap_cqrs(command_bus, query_bus)
    ↓
Register handler factories to buses
    ↓
Application Ready
```

### Request Flow

```
HTTP Request → Router
    ↓
Dispatch Command via CommandBus
    ↓
CommandBus finds registered factory
    ↓
Factory creates:
    - Fresh database session
    - Fresh repository with session
    - Handler instance with repo
    ↓
Execute handler.handle(command)
    ↓
Auto-commit/rollback via context manager
    ↓
Return Result to Router
```

## Rationale

### Why Factory Pattern?

1. **Fresh Dependencies Per Request:**
   - Each invocation gets new session
   - No shared state between requests
   - Thread-safe by design

2. **Separation of Concerns:**
   - Routers don't know about repositories
   - Handlers don't know about session management
   - Bootstrap centralizes dependency wiring

3. **Testability:**
   - Easy to test handlers with mock repositories
   - Factory pattern allows dependency injection
   - No global state to reset in tests

4. **Transaction Management:**
   - Session lifecycle tied to handler invocation
   - Auto-commit on success, auto-rollback on error
   - Clear transaction boundaries

5. **Scalability:**
   - Adding new handlers is straightforward
   - Pattern is consistent across all bounded contexts
   - Easy to understand and maintain

### Why Not Dependency Injection Container?

We DO use a DI container (`dependency-injector`) for:
- CommandBus singleton
- QueryBus singleton
- Cache providers
- Configuration

But we DON'T use it for handler registration because:
- Per-request lifecycle doesn't fit singleton pattern
- Factory pattern is more explicit
- No runtime reflection/magic needed
- Easier to debug and understand

### Shared vs Fresh Dependencies

**Shared (Stateless - Created Once):**
- Domain services (no state)
- Validation services
- Configuration

**Fresh (Stateful - Created Per Request):**
- Database sessions
- Repositories (wrap sessions)
- Unit of Work
- Handler instances

## Implementation Guidelines

### Adding a New Command Handler

```python
# 1. Create Command and Handler
# src/application/orders/commands/create_order.py
@dataclass(frozen=True, kw_only=True)
class CreateOrderCommand(BaseCommand):
    customer_id: str
    items: list[OrderItem]

class CreateOrderHandler(CommandHandler[CreateOrderCommand, OrderAggregate]):
    def __init__(self, order_repository: IOrderRepository, pricing_service: PricingService):
        self._repository = order_repository
        self._pricing_service = pricing_service

    async def handle(self, command: CreateOrderCommand) -> Result[OrderAggregate, Exception]:
        # Implementation
        ...

# 2. Register in Bootstrap
# src/infrastructure/di/cqrs_bootstrap.py
async def register_order_handlers(command_bus: CommandBus, query_bus: QueryBus):
    # Shared stateless service
    pricing_service = PricingService()

    async def create_order_handler(cmd: CreateOrderCommand):
        db = get_database_session()
        async with db.session() as session:
            repo = SQLAlchemyOrderRepository(session)
            handler = CreateOrderHandler(
                order_repository=repo,
                pricing_service=pricing_service  # Shared
            )
            return await handler.handle(cmd)

    command_bus.register(CreateOrderCommand, create_order_handler)

# 3. Call from bootstrap_cqrs
async def bootstrap_cqrs(command_bus: CommandBus, query_bus: QueryBus):
    await register_user_handlers(command_bus, query_bus)
    await register_order_handlers(command_bus, query_bus)  # ← Add here
```

### Testing Handlers

```python
# Unit Test (Mock Repository)
@pytest.mark.asyncio
async def test_create_order_handler():
    # Arrange
    mock_repo = AsyncMock(spec=IOrderRepository)
    pricing_service = PricingService()
    handler = CreateOrderHandler(mock_repo, pricing_service)

    command = CreateOrderCommand(customer_id="123", items=[...])

    # Act
    result = await handler.handle(command)

    # Assert
    assert result.is_ok()
    mock_repo.save.assert_called_once()
```

### Testing Factory

```python
# Integration Test (Real Bootstrap)
@pytest.mark.asyncio
async def test_command_bus_with_factory():
    # Arrange
    command_bus = CommandBus()
    query_bus = QueryBus()
    await bootstrap_cqrs(command_bus, query_bus)

    command = CreateUserCommand(email="test@example.com", password="Pass123!")

    # Act
    result = await command_bus.dispatch(command)

    # Assert
    assert result.is_ok()
    # Verify in database
    ...
```

## Dependency Lifecycle Summary

| Dependency Type | Lifecycle | Created Where | Example |
|----------------|-----------|---------------|---------|
| CommandBus | Singleton | DI Container | `container.command_bus()` |
| QueryBus | Singleton | DI Container | `container.query_bus()` |
| Domain Service | Singleton | Bootstrap function | `UserDomainService()` |
| Database Session | Per Request | Handler factory | `async with db.session()` |
| Repository | Per Request | Handler factory | `SQLAlchemyUserRepository(session)` |
| Handler | Per Invocation | Handler factory | `CreateUserHandler(repo, service)` |

## Consequences

### Positive

- **Thread-Safe:** Fresh dependencies per request
- **Clean Architecture:** Layers properly separated
- **Testable:** Easy to test handlers in isolation
- **Maintainable:** Consistent pattern across all handlers
- **Scalable:** Easy to add new handlers
- **Explicit:** Clear dependency creation and lifecycle

### Negative

- **Boilerplate:** Factory function needed for each handler
- **Indirection:** Extra layer between bus and handler
- **Memory:** Creates objects per request (acceptable trade-off)

### Neutral

- **Pattern Consistency:** All handlers follow same registration pattern
- **Documentation:** Requires clear documentation of pattern

## Performance Considerations

### Factory Overhead

**Per Request:**
- Create database session: ~0.1ms
- Create repository instance: ~0.01ms
- Create handler instance: ~0.01ms
- **Total overhead:** ~0.12ms

**Acceptable because:**
- Database query time >> overhead (~10-100ms)
- Thread safety and correctness more important
- Python GC handles cleanup efficiently

### Memory Usage

**Per Request:**
- Session object: ~1KB
- Repository object: ~0.5KB
- Handler object: ~0.5KB
- **Total:** ~2KB per request

**Acceptable because:**
- Objects garbage collected after request
- No memory leaks from shared state
- Scales linearly with concurrent requests

## Alternatives Considered

### Alternative 1: Handler Singletons with Dependency Injection

**Pattern:**
```python
handler = CreateUserHandler(
    user_repository_factory=lambda: get_repo(),
    user_service=user_service
)
command_bus.register(CreateUserCommand, handler.handle)
```

**Pros:**
- Handler created once
- Less object creation

**Cons:**
- Complex factory management
- Still need per-request session handling
- Harder to test

**Rejected because:** Complexity doesn't justify minor performance gain.

### Alternative 2: Middleware for Dependency Injection

**Pattern:**
```python
class DependencyMiddleware:
    async def __call__(self, command, next_handler):
        async with db.session() as session:
            # Inject dependencies into command
            command._session = session
            return await next_handler(command)
```

**Pros:**
- Centralized dependency injection

**Cons:**
- Pollutes command objects with infrastructure
- Violates command immutability
- Hidden dependencies

**Rejected because:** Commands should be pure data, not carry infrastructure.

### Alternative 3: Service Locator Pattern

**Pattern:**
```python
class ServiceLocator:
    @staticmethod
    def get_repository():
        session = get_current_session()
        return SQLAlchemyUserRepository(session)

# In handler
repo = ServiceLocator.get_repository()
```

**Pros:**
- Simple to implement
- Handlers independent

**Cons:**
- Anti-pattern (hidden dependencies)
- Hard to test (global state)
- Couples to service locator

**Rejected because:** Violates dependency injection principles.

## Related Decisions

- ADR-001: CQRS Pattern (command/query separation)
- ADR-004: Unit of Work Strategy (session lifecycle)
- DI Container usage for singletons

## Review Notes

- **Review date:** 2025-Q2
- **Review trigger:** If adding >50 handlers becomes burdensome
- **Consider:** Code generation for factory functions if needed

## References

- [Martin Fowler - Dependency Injection](https://martinfowler.com/articles/injection.html)
- [Gang of Four - Factory Pattern](https://refactoring.guru/design-patterns/factory-method)
- [Python Dependency Injector](https://python-dependency-injector.ets-labs.org/)
- [Clean Architecture by Robert C. Martin](https://www.amazon.com/Clean-Architecture-Craftsmans-Software-Structure/dp/0134494164)
