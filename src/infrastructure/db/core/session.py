"""Async SQLAlchemy session factory with connection pooling.

**Feature: infrastructure-code-review**
**Validates: Requirements 1.1, 1.2, 1.4**
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel

from infrastructure.errors import DatabaseError

logger = logging.getLogger(__name__)


class DatabaseSession:
    """Database session manager with async support.

    Manages database connections and sessions using SQLAlchemy 2.0
    async features with connection pooling.
    """

    def __init__(
        self,
        database_url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        echo: bool = False,
    ) -> None:
        """Initialize database session manager.

        Args:
            database_url: Database connection URL.
            pool_size: Connection pool size (must be >= 1).
            max_overflow: Max overflow connections (must be >= 0).
            echo: Echo SQL statements.

        Raises:
            ValueError: If database_url is empty or pool parameters are invalid.
        """
        # Validate database_url
        if not database_url or not database_url.strip():
            raise ValueError("database_url cannot be empty or whitespace")

        # Validate pool parameters
        if pool_size < 1:
            raise ValueError(f"pool_size must be >= 1, got {pool_size}")
        if max_overflow < 0:
            raise ValueError(f"max_overflow must be >= 0, got {max_overflow}")

        self._engine: AsyncEngine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=echo,
            pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        """Get the async engine."""
        return self._engine

    async def create_tables(self) -> None:
        """Create all tables defined in SQLModel metadata."""
        async with self._engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all tables defined in SQLModel metadata."""
        async with self._engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)

    async def close(self) -> None:
        """Close the database engine and all connections."""
        await self._engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with automatic transaction management.

        Yields:
            AsyncSession: Database session.

        Raises:
            Exception: Re-raises any exception after rollback with preserved chain.
        """
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(
                "Database session error, rolling back",
                extra={"error_type": type(e).__name__, "error_message": str(e)},
            )
            await session.rollback()
            raise
        finally:
            await session.close()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session for FastAPI dependency injection.

        Yields:
            AsyncSession: Database session.
        """
        async with self.session() as session:
            yield session


# Global database session instance (initialized in app startup)
_db_session: DatabaseSession | None = None


def get_database_session() -> DatabaseSession:
    """Get the global database session manager.

    Returns:
        DatabaseSession: Database session manager.

    Raises:
        DatabaseError: If database not initialized.
    """
    if _db_session is None:
        raise DatabaseError("Database not initialized. Call init_database first.")
    return _db_session


def init_database(
    database_url: str,
    pool_size: int = 5,
    max_overflow: int = 10,
    echo: bool = False,
) -> DatabaseSession:
    """Initialize the global database session manager.

    Args:
        database_url: Database connection URL.
        pool_size: Connection pool size.
        max_overflow: Max overflow connections.
        echo: Echo SQL statements.

    Returns:
        DatabaseSession: Initialized database session manager.
    """
    global _db_session
    _db_session = DatabaseSession(
        database_url=database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        echo=echo,
    )
    return _db_session


async def close_database() -> None:
    """Close the global database connection."""
    global _db_session
    if _db_session is not None:
        await _db_session.close()
        _db_session = None


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async session for FastAPI dependency injection.

    This function provides a database session that can be used with FastAPI's
    Depends() for automatic dependency injection in route handlers.

    **Feature: infrastructure-examples-integration-fix**
    **Validates: Requirements 1.1, 1.3, 1.4**

    Yields:
        AsyncSession: Database session with automatic transaction management.
            The session commits on successful completion and rolls back on error.

    Raises:
        DatabaseError: If database not initialized. Call init_database first.

    Example:
        >>> from fastapi import Depends
        >>> from infrastructure.db.session import get_async_session
        >>>
        >>> @router.get("/items")
        >>> async def list_items(session: AsyncSession = Depends(get_async_session)):
        ...     # Use session for database operations
        ...     pass
    """
    db = get_database_session()  # Raises DatabaseError if not initialized
    async with db.session() as session:
        yield session
