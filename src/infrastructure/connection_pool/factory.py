"""Connection factory protocols and base classes.

**Feature: full-codebase-review-2025, Task 1.1: Refactor connection_pool**
**Validates: Requirements 9.2**
"""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class ConnectionFactory[T](Protocol):
    """Protocol for connection factories."""

    async def create(self) -> T:
        """Create a new connection."""
        ...

    async def destroy(self, connection: T) -> None:
        """Destroy a connection."""
        ...

    async def validate(self, connection: T) -> bool:
        """Validate connection health."""
        ...


class BaseConnectionFactory[T](ABC):
    """Base class for connection factories."""

    @abstractmethod
    async def create(self) -> T:
        """Create a new connection."""
        ...

    @abstractmethod
    async def destroy(self, connection: T) -> None:
        """Destroy a connection."""
        ...

    @abstractmethod
    async def validate(self, connection: T) -> bool:
        """Validate connection health."""
        ...
