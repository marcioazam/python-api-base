"""Unit of Work interface for transaction management.

The Unit of Work pattern maintains a list of objects affected by a
business transaction and coordinates the writing out of changes.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 6.3**
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Self


class UnitOfWork(ABC):
    """Abstract Unit of Work interface.
    
    The Unit of Work pattern:
    - Maintains a list of objects affected by a business transaction
    - Coordinates writing out changes
    - Ensures atomicity of operations
    
    Usage:
        async with uow:
            user = await uow.users.get(user_id)
            user.update_email(new_email)
            await uow.commit()
    """
    
    @abstractmethod
    async def __aenter__(self) -> Self:
        """Enter the unit of work context."""
        ...
    
    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the unit of work context."""
        ...
    
    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        ...
    
    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        ...
    
    @abstractmethod
    async def flush(self) -> None:
        """Flush pending changes without committing."""
        ...
