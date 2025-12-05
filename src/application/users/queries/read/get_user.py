"""Get user queries and handlers.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 3.2**
"""

from dataclasses import dataclass
from typing import Any

from application.common.cqrs.handlers import QueryHandler
from core.base.cqrs.query import BaseQuery
from core.base.patterns.result import Err, Ok, Result
from domain.users.repositories import IUserReadRepository, IUserRepository


@dataclass(frozen=True, kw_only=True)
class GetUserByIdQuery(BaseQuery[dict[str, Any] | None]):
    """Query to get a user by ID."""

    user_id: str

    def get_cache_key(self) -> str:
        return f"user:{self.user_id}"


@dataclass(frozen=True, kw_only=True)
class GetUserByEmailQuery(BaseQuery[dict[str, Any] | None]):
    """Query to get a user by email."""

    email: str

    def get_cache_key(self) -> str:
        return f"user:email:{self.email}"


class GetUserByIdHandler(QueryHandler[GetUserByIdQuery, dict[str, Any] | None]):
    """Handler for GetUserByIdQuery."""

    def __init__(self, repository: IUserRepository) -> None:
        self._repository = repository

    async def handle(
        self, query: GetUserByIdQuery
    ) -> Result[dict[str, Any] | None, Exception]:
        """Handle get user by ID query."""
        try:
            user = await self._repository.get_by_id(query.user_id)
            if user is None:
                return Ok(None)
            return Ok(user.model_dump())
        except Exception as e:
            return Err(e)


class GetUserByEmailHandler(QueryHandler[GetUserByEmailQuery, dict[str, Any] | None]):
    """Handler for GetUserByEmailQuery."""

    def __init__(self, repository: IUserRepository) -> None:
        self._repository = repository

    async def handle(
        self, query: GetUserByEmailQuery
    ) -> Result[dict[str, Any] | None, Exception]:
        """Handle get user by email query."""
        try:
            user = await self._repository.get_by_email(query.email)
            if user is None:
                return Ok(None)
            return Ok(user.model_dump())
        except Exception as e:
            return Err(e)


@dataclass(frozen=True, kw_only=True)
class ListUsersQuery(BaseQuery[list[dict[str, Any]]]):
    """Query to list users with pagination."""

    page: int = 1
    page_size: int = 20
    include_inactive: bool = False

    def get_cache_key(self) -> str:
        return f"users:list:{self.page}:{self.page_size}:{self.include_inactive}"


class ListUsersHandler(QueryHandler[ListUsersQuery, list[dict[str, Any]]]):
    """Handler for ListUsersQuery."""

    def __init__(self, read_repository: IUserReadRepository) -> None:
        self._read_repository = read_repository

    async def handle(
        self, query: ListUsersQuery
    ) -> Result[list[dict[str, Any]], Exception]:
        """Handle list users query."""
        try:
            offset = (query.page - 1) * query.page_size
            users = await self._read_repository.list_all(
                limit=query.page_size,
                offset=offset,
                include_inactive=query.include_inactive,
            )
            return Ok(users)
        except Exception as e:
            return Err(e)


@dataclass(frozen=True, kw_only=True)
class CountUsersQuery(BaseQuery[int]):
    """Query to count total users.

    **Feature: code-review-interface-improvements**
    **Validates: P1-1 - Correct pagination total count**
    """

    include_inactive: bool = False

    def get_cache_key(self) -> str:
        """Generate cache key for count query."""
        return f"users:count:{self.include_inactive}"


class CountUsersHandler(QueryHandler[CountUsersQuery, int]):
    """Handler for counting total users.

    **Feature: code-review-interface-improvements**
    **Validates: P1-1 - Correct pagination total count**
    """

    def __init__(self, read_repository: IUserReadRepository) -> None:
        self._read_repository = read_repository

    async def handle(self, query: CountUsersQuery) -> Result[int, Exception]:
        """Handle count users query."""
        try:
            count = await self._read_repository.count_all(
                include_inactive=query.include_inactive,
            )
            return Ok(count)
        except Exception as e:
            return Err(e)
