# ADR-004: Unit of Work Strategy

**Status:** Accepted

**Date:** 2025-01-02

**Deciders:** Architecture Team

**Technical Story:** Clarify the transaction management strategy across BaseUseCase (explicit UoW) and CQRS handlers (implicit session context manager).

---

## Context

The system has two patterns for managing database transactions:

### Pattern 1: Explicit Unit of Work (BaseUseCase)
Located in `src/application/common/base/use_case.py`:

```python
class BaseUseCase[TEntity, TId](ABC):
    async def create(self, data: Any) -> Result[TEntity, UseCaseError]:
        uow = await self._get_unit_of_work()
        repo = await self._get_repository()

        async with uow:  # ✅ Explicit UoW
            entity = await repo.create(data)
            await uow.commit()  # Explicit commit
            await self._after_create(entity)
            return Ok(entity)
```

### Pattern 2: Session Context Manager (CQRS Handlers)
Located in `src/infrastructure/di/cqrs_bootstrap.py`:

```python
async def create_user_handler(cmd: CreateUserCommand):
    db = get_database_session()
    async with db.session() as session:  # ✅ Implicit UoW via context manager
        repo = SQLAlchemyUserRepository(session)
        handler = CreateUserHandler(repo, user_service)
        return await handler.handle(cmd)
        # Auto-commit on exit if no exception
```

### Pattern 3: Transaction Middleware (Available)
Located in `src/application/common/middleware/transaction.py`:

```python
class TransactionMiddleware:
    """Wraps command execution in a transaction."""
    async def __call__(self, command: Any, next_handler: Callable) -> Result:
        uow = self._uow_factory()
        async with uow:
            result = await next_handler(command)
            if isinstance(result, Ok):
                await uow.commit()
            else:
                await uow.rollback()
            return result
```

**Status:** ⚠️ Created but not integrated

## Problem

Three transaction patterns create confusion:
- When to use explicit UoW vs session context manager?
- Are they equivalent or is one preferred?
- Should TransactionMiddleware be activated?
- How to ensure transactional integrity across all paths?

## Decision

**We adopt Session-per-Request Context Manager as the primary strategy**, with the following clarifications:

### Primary Strategy: Session Context Manager (ACTIVE)

**Used by:** CQRS command/query handlers (current production code)

**Pattern:**
```python
async def handler_factory(cmd: Command):
    db = get_database_session()
    async with db.session() as session:  # ✅ Transaction starts
        repo = Repository(session)
        handler = Handler(repo)
        result = await handler.handle(cmd)
        # ✅ Auto-commit on success (exit)
        # ✅ Auto-rollback on exception
        return result
```

**Characteristics:**
- **Implicit UoW:** Session context manager handles begin/commit/rollback
- **Scope:** One transaction per handler invocation
- **Commit:** Automatic on clean exit
- **Rollback:** Automatic on exception
- **Isolation:** Each request gets fresh session

**Why This is UoW:**
- Session IS the Unit of Work in SQLAlchemy
- Context manager provides transaction boundaries
- Commit/rollback handled by `__aexit__`
- Same guarantees as explicit UoW pattern

### Secondary Pattern: Explicit UoW (BaseUseCase)

**Used by:** Generic BaseUseCase class (available for use but not primary)

**Pattern:**
```python
class BaseUseCase[TEntity, TId](ABC):
    async def create(self, data: Any) -> Result[TEntity, UseCaseError]:
        uow = await self._get_unit_of_work()
        async with uow:
            entity = await repo.create(data)
            await uow.commit()  # Explicit
            return Ok(entity)
```

**Characteristics:**
- **Explicit UoW:** Separate UoW object from session
- **Scope:** Controlled by use case method
- **Commit:** Explicit `await uow.commit()`
- **Flexibility:** Can span multiple repositories

**When to Use:**
- Multi-repository operations in single transaction
- Complex sagas or workflows
- When explicit transaction control needed

### Transaction Middleware: NOT ACTIVE

**Status:** Available but not integrated

**Reason:** Session context manager already provides transaction management

**Future Use:** Consider if we need:
- Cross-cutting transaction logging
- Automatic transaction retry logic
- Distributed transactions

## Rationale

### Why Session Context Manager?

1. **Simplicity:** Pythonic context manager pattern
2. **Safety:** Automatic rollback on exceptions
3. **Performance:** No extra abstraction layer
4. **Standard:** SQLAlchemy recommended pattern
5. **Testability:** Easy to mock session

### Why Not Explicit UoW Everywhere?

1. **Overhead:** Extra abstraction for most cases
2. **Complexity:** More code to maintain
3. **Redundancy:** Session already provides UoW semantics

### Why Not Transaction Middleware?

1. **Redundancy:** Session context manager already manages transactions
2. **Complexity:** Adds middleware layer for existing functionality
3. **Performance:** Extra wrapping without benefit
4. **Flexibility Lost:** Harder to control commit timing per handler

## Equivalence Proof

**Session Context Manager:**
```python
async with db.session() as session:
    # Work here
    pass  # Auto-commit on success
```

**Is equivalent to Explicit UoW:**
```python
async with uow:
    # Work here
    await uow.commit()
```

**Both provide:**
- ✅ Transaction begin
- ✅ Isolation
- ✅ Commit on success
- ✅ Rollback on exception
- ✅ Resource cleanup

## Implementation Guidelines

### For Command Handlers

```python
# ✅ CORRECT: Session context manager
async def create_user_handler(cmd: CreateUserCommand):
    db = get_database_session()
    async with db.session() as session:
        repo = SQLAlchemyUserRepository(session)
        handler = CreateUserHandler(repo, user_service)
        return await handler.handle(cmd)
```

### For Query Handlers

```python
# ✅ CORRECT: Session context manager (read-only)
async def get_user_handler(query: GetUserByIdQuery):
    db = get_database_session()
    async with db.session() as session:
        repo = SQLAlchemyUserRepository(session)
        handler = GetUserByIdHandler(repo)
        return await handler.handle(query)
```

### For Complex Multi-Repository Operations

```python
# ✅ CORRECT: Explicit UoW when needed
class TransferFundsUseCase(BaseUseCase[Transfer, str]):
    async def execute(self, from_id: str, to_id: str, amount: float):
        uow = await self._get_unit_of_work()

        async with uow:
            account_repo = await self._get_account_repo()
            transfer_repo = await self._get_transfer_repo()

            # Multiple repositories, single transaction
            from_account = await account_repo.get(from_id)
            to_account = await account_repo.get(to_id)

            from_account.debit(amount)
            to_account.credit(amount)

            await account_repo.update(from_account)
            await account_repo.update(to_account)

            transfer = Transfer.create(from_id, to_id, amount)
            await transfer_repo.create(transfer)

            await uow.commit()  # All or nothing
            return Ok(transfer)
```

### Error Handling

```python
# ✅ CORRECT: Exceptions trigger automatic rollback
async with db.session() as session:
    repo = SQLAlchemyUserRepository(session)
    handler = CreateUserHandler(repo, service)

    result = await handler.handle(cmd)

    if result.is_err():
        # No explicit rollback needed
        # Exception in handler → auto-rollback
        return result

    # Success → auto-commit
    return result
```

## Testing Strategy

### Unit Tests (Mock Session)

```python
@pytest.mark.asyncio
async def test_handler_transaction_commits_on_success():
    mock_session = AsyncMock()
    repo = SQLAlchemyUserRepository(mock_session)
    handler = CreateUserHandler(repo, service)

    result = await handler.handle(command)

    assert result.is_ok()
    # Session commit called by context manager
    mock_session.commit.assert_called_once()
```

### Integration Tests (Real DB)

```python
@pytest.mark.asyncio
async def test_transaction_rollback_on_failure(db_session):
    async with db_session() as session:
        repo = SQLAlchemyUserRepository(session)
        handler = CreateUserHandler(repo, service)

        # Simulate failure
        with pytest.raises(DatabaseError):
            await handler.handle(invalid_command)

    # Verify rollback occurred
    async with db_session() as session:
        repo = SQLAlchemyUserRepository(session)
        user = await repo.get_by_email("test@example.com")
        assert user is None  # Not persisted due to rollback
```

## Consequences

### Positive

- **Simplicity:** One primary pattern (session context manager)
- **Safety:** Automatic rollback on errors
- **Performance:** No extra abstraction layers
- **Pythonic:** Standard context manager pattern
- **Testable:** Easy to test with mocks

### Negative

- **Two Patterns Exist:** Session context manager + explicit UoW (BaseUseCase)
- **Documentation Needed:** Must clarify when to use each
- **Migration:** Existing BaseUseCase code remains

### Neutral

- **BaseUseCase Available:** Can use explicit UoW when complexity requires
- **Transaction Middleware:** Available for future needs

## Migration Guide

### From BaseUseCase to CQRS Handlers

**Before (BaseUseCase):**
```python
class UserUseCase(BaseUseCase[User, str]):
    async def create_user(self, data: CreateUserDTO) -> Result[User, Error]:
        uow = await self._get_unit_of_work()
        async with uow:
            user = await self._repo.create(data)
            await uow.commit()
            return Ok(user)
```

**After (CQRS Handler):**
```python
class CreateUserHandler(CommandHandler[CreateUserCommand, UserAggregate]):
    async def handle(self, cmd: CreateUserCommand) -> Result[UserAggregate, Exception]:
        # Session managed by handler factory (bootstrap)
        user = UserAggregate.create(...)
        saved = await self._repository.save(user)
        return Ok(saved)

# In bootstrap:
async def create_user_handler(cmd: CreateUserCommand):
    async with db.session() as session:  # ✅ Transaction here
        repo = SQLAlchemyUserRepository(session)
        handler = CreateUserHandler(repo, service)
        return await handler.handle(cmd)
```

## Alternatives Considered

### Alternative 1: Transaction Middleware for All

**Pros:**
- Centralized transaction management
- Consistent across all commands
- Easy to add logging/metrics

**Cons:**
- Redundant with session context manager
- Extra layer of abstraction
- Less flexible for special cases

**Rejected because:** Session context manager already provides needed functionality.

### Alternative 2: Explicit UoW Everywhere

**Pros:**
- Uniform pattern
- More explicit control

**Cons:**
- More boilerplate
- Slower (extra abstraction)
- Less Pythonic

**Rejected because:** Context manager is more idiomatic and sufficient.

### Alternative 3: No Transaction Management

**Pros:**
- Simplest possible
- Let SQLAlchemy handle it

**Cons:**
- No explicit transaction boundaries
- Hard to control commit/rollback timing
- Difficult to test

**Rejected because:** Explicit transaction boundaries are critical for data integrity.

## Related Decisions

- ADR-001: CQRS Pattern (command/query handlers)
- ADR-003: Resilience Layers (error handling)
- ADR-005: CQRS Bootstrap Pattern (handler factory setup)

## Review Notes

- **Review date:** 2025-Q2
- **Review trigger:** If transaction-related bugs emerge
- **Consider:** Transaction middleware if cross-cutting concerns arise

## References

- [SQLAlchemy Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [Martin Fowler - Unit of Work](https://martinfowler.com/eaaCatalog/unitOfWork.html)
- [Python Context Managers](https://docs.python.org/3/library/contextlib.html)
- [DDD Aggregates and Transactions](https://www.domainlanguage.com/)
