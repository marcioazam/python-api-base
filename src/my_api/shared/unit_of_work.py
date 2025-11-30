"""Unit of Work pattern for transaction management."""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Self
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession


class IUnitOfWork(ABC):
    """Abstract Unit of Work interface.

    Coordinates the work of multiple repositories by maintaining
    a list of objects affected by a business transaction and
    coordinates the writing out of changes.
    """

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        ...

    @abstractmethod
    async def __aenter__(self) -> Self:
        """Enter the context manager."""
        ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager."""
        ...


class SQLAlchemyUnitOfWork(IUnitOfWork):
    """SQLAlchemy implementation of Unit of Work.

    Wraps database operations in a transaction that can be
    committed or rolled back atomically.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize Unit of Work.

        Args:
            session: SQLAlchemy async session.
        """
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Get the underlying session."""
        return self._session

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self._session.rollback()

    async def __aenter__(self) -> Self:
        """Enter the context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager, rolling back on error."""
        if exc_type is not None:
            await self.rollback()
        await self._session.close()


@asynccontextmanager
async def transaction(uow: IUnitOfWork) -> AsyncGenerator[IUnitOfWork, None]:
    """Context manager for transactional operations.

    Usage:
        async with transaction(uow) as unit:
            await repo.create(entity)
            await repo.update(other_entity)
        # Auto-commits on success, rollbacks on error

    Args:
        uow: Unit of Work instance.

    Yields:
        The Unit of Work for use in the transaction.
    """
    try:
        yield uow
        await uow.commit()
    except Exception:
        await uow.rollback()
        raise


# =============================================================================
# Generic Async Context Managers
# =============================================================================


class AsyncResource[T]:
    """Generic async context manager for resource management.

    Provides a type-safe way to manage async resources with automatic
    cleanup on exit.

    Type Parameters:
        T: The type of resource being managed.

    Usage:
        class DatabaseConnection(AsyncResource[Connection]):
            async def acquire(self) -> Connection:
                return await pool.acquire()

            async def release(self, resource: Connection) -> None:
                await pool.release(resource)

        async with DatabaseConnection() as conn:
            await conn.execute("SELECT 1")
    """

    async def acquire(self) -> T:
        """Acquire the resource.

        Override this method to implement resource acquisition.

        Returns:
            The acquired resource.
        """
        raise NotImplementedError("Subclasses must implement acquire()")

    async def release(self, resource: T) -> None:
        """Release the resource.

        Override this method to implement resource cleanup.

        Args:
            resource: The resource to release.
        """
        pass

    async def __aenter__(self) -> T:
        """Enter the context and acquire the resource."""
        self._resource = await self.acquire()
        return self._resource

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context and release the resource."""
        await self.release(self._resource)


class AsyncLock[T]:
    """Generic async context manager for lock-protected operations.

    Provides a type-safe way to execute operations under a lock
    and return a result.

    Type Parameters:
        T: The type of result from the protected operation.

    Usage:
        lock = asyncio.Lock()

        async with AsyncLock(lock, lambda: fetch_data()) as result:
            process(result)
    """

    def __init__(
        self,
        lock: "asyncio.Lock",
        operation: "Callable[[], Awaitable[T]]",
    ) -> None:
        """Initialize the lock context.

        Args:
            lock: The asyncio lock to use.
            operation: The async operation to execute under the lock.
        """
        self._lock = lock
        self._operation = operation
        self._result: T | None = None

    async def __aenter__(self) -> T:
        """Acquire lock and execute operation."""
        await self._lock.acquire()
        try:
            self._result = await self._operation()
            return self._result
        except Exception:
            self._lock.release()
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Release the lock."""
        self._lock.release()


class AsyncTimeout[T]:
    """Generic async context manager with timeout.

    Wraps an async operation with a timeout, raising TimeoutError
    if the operation takes too long.

    Type Parameters:
        T: The type of result from the operation.

    Usage:
        async with AsyncTimeout(5.0, fetch_data) as result:
            process(result)  # Raises TimeoutError if fetch_data takes > 5s
    """

    def __init__(
        self,
        timeout_seconds: float,
        operation: "Callable[[], Awaitable[T]]",
    ) -> None:
        """Initialize the timeout context.

        Args:
            timeout_seconds: Maximum time to wait for the operation.
            operation: The async operation to execute.
        """
        self._timeout = timeout_seconds
        self._operation = operation
        self._result: T | None = None

    async def __aenter__(self) -> T:
        """Execute operation with timeout."""
        import asyncio

        self._result = await asyncio.wait_for(
            self._operation(),
            timeout=self._timeout,
        )
        return self._result

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context (no cleanup needed)."""
        pass


@asynccontextmanager
async def managed_resource[T](
    acquire: "Callable[[], Awaitable[T]]",
    release: "Callable[[T], Awaitable[None]]",
) -> AsyncGenerator[T, None]:
    """Generic context manager for any async resource.

    A functional approach to resource management that doesn't require
    subclassing.

    Type Parameters:
        T: The type of resource being managed.

    Args:
        acquire: Async function to acquire the resource.
        release: Async function to release the resource.

    Yields:
        The acquired resource.

    Usage:
        async with managed_resource(
            acquire=lambda: pool.acquire(),
            release=lambda conn: pool.release(conn),
        ) as conn:
            await conn.execute("SELECT 1")
    """
    resource = await acquire()
    try:
        yield resource
    finally:
        await release(resource)


@asynccontextmanager
async def atomic_operation[T](
    operation: "Callable[[], Awaitable[T]]",
    on_success: "Callable[[T], Awaitable[None]] | None" = None,
    on_failure: "Callable[[Exception], Awaitable[None]] | None" = None,
) -> AsyncGenerator[T, None]:
    """Generic context manager for atomic operations with callbacks.

    Executes an operation and calls success/failure callbacks based
    on the outcome.

    Type Parameters:
        T: The type of result from the operation.

    Args:
        operation: The async operation to execute.
        on_success: Optional callback on successful completion.
        on_failure: Optional callback on failure.

    Yields:
        The result of the operation.

    Usage:
        async with atomic_operation(
            operation=lambda: create_order(data),
            on_success=lambda order: send_confirmation(order),
            on_failure=lambda e: log_error(e),
        ) as order:
            print(f"Created order: {order.id}")
    """
    try:
        result = await operation()
        yield result
        if on_success:
            await on_success(result)
    except Exception as e:
        if on_failure:
            await on_failure(e)
        raise


# Import for type hints
import asyncio
from collections.abc import Awaitable, Callable
