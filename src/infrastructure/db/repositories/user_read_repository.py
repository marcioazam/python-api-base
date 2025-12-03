"""SQLAlchemy implementation of User read repository.

Read-optimized repository for user queries that returns dictionaries
instead of domain aggregates for better performance.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 6.2**
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.users_models import UserModel


class SQLAlchemyUserReadRepository:
    """SQLAlchemy implementation of IUserReadRepository.

    Optimized for read operations, returns dictionaries
    instead of domain aggregates to avoid unnecessary hydration.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Get user data by ID."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_dict(model)

    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search users by query string.

        Searches in email, username, and display_name fields.

        Args:
            query: Search query string.
            limit: Maximum number of results.

        Returns:
            List of user dictionaries.
        """
        search_pattern = f"%{query.lower()}%"
        stmt = (
            select(UserModel)
            .where(
                (UserModel.email.like(search_pattern))
                | (UserModel.username.like(search_pattern))
                | (UserModel.display_name.like(search_pattern))
            )
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_dict(m) for m in models]

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        include_inactive: bool = False,
    ) -> list[dict[str, Any]]:
        """List all users with pagination.

        Args:
            limit: Maximum number of users to return.
            offset: Number of users to skip.
            include_inactive: If True, include inactive users.

        Returns:
            List of user dictionaries.
        """
        stmt = select(UserModel).order_by(UserModel.created_at.desc())

        if not include_inactive:
            stmt = stmt.where(UserModel.is_active)

        stmt = stmt.limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_dict(m) for m in models]

    def _to_dict(self, model: UserModel) -> dict[str, Any]:
        """Convert database model to dictionary.

        Args:
            model: UserModel instance.

        Returns:
            Dictionary with user data.
        """
        return {
            "id": model.id,
            "email": model.email,
            "username": model.username,
            "display_name": model.display_name,
            "is_active": model.is_active,
            "is_verified": model.is_verified,
            "created_at": model.created_at.isoformat() if model.created_at else None,
            "updated_at": model.updated_at.isoformat() if model.updated_at else None,
            "last_login_at": (
                model.last_login_at.isoformat() if model.last_login_at else None
            ),
        }
