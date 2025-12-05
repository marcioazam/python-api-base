"""Repository interfaces (Ports) for the Users bounded context.

These are abstract interfaces that define how the domain layer
interacts with persistence. Implementations are in infrastructure.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 2.7**
"""

from abc import ABC, abstractmethod
from typing import Protocol

from domain.users.aggregates import UserAggregate


class IUserRepository(ABC):
    """Abstract repository interface for User aggregates.

    This is a Port in Hexagonal Architecture - it defines the contract
    that infrastructure adapters must implement.
    """

    @abstractmethod
    async def get_by_id(self, user_id: str) -> UserAggregate | None:
        """Get a user by ID.

        Args:
            user_id: User identifier.

        Returns:
            UserAggregate if found, None otherwise.
        """
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> UserAggregate | None:
        """Get a user by email address.

        Args:
            email: User email address.

        Returns:
            UserAggregate if found, None otherwise.
        """
        ...

    @abstractmethod
    async def save(self, user: UserAggregate) -> UserAggregate:
        """Save a user aggregate.

        Args:
            user: User aggregate to save.

        Returns:
            Saved user aggregate with updated fields.
        """
        ...

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """Delete a user by ID.

        Args:
            user_id: User identifier.

        Returns:
            True if deleted, False if not found.
        """
        ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """Check if a user exists with the given email.

        Args:
            email: Email address to check.

        Returns:
            True if user exists, False otherwise.
        """
        ...

    @abstractmethod
    async def list_active(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UserAggregate]:
        """List active users with pagination.

        Args:
            limit: Maximum number of users to return.
            offset: Number of users to skip.

        Returns:
            List of active user aggregates.
        """
        ...

    @abstractmethod
    async def count_active(self) -> int:
        """Count active users.

        Returns:
            Number of active users.
        """
        ...


class IUserReadRepository(Protocol):
    """Read-only repository for user queries.

    Used by query handlers for optimized read operations.
    """

    async def get_by_id(self, user_id: str) -> dict | None:
        """Get user data by ID."""
        ...

    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[dict]:
        """Search users by query string."""
        ...

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        include_inactive: bool = False,
    ) -> list[dict]:
        """List all users with pagination."""
        ...

    async def count_all(
        self,
        include_inactive: bool = False,
    ) -> int:
        """Count total users.

        Args:
            include_inactive: If True, include inactive users in count.

        Returns:
            Total number of users matching criteria.
        """
        ...
