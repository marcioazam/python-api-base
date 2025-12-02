"""Get user query and handler.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 3.2**
"""

from dataclasses import dataclass
from typing import Any

from core.base.query import BaseQuery
from core.base.result import Result, Ok, Err
from application.common.cqrs.handlers import QueryHandler
from domain.users.repositories import IUserRepository


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
