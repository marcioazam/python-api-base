"""SQLAlchemy implementation of User repository.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 6.2**
"""

from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from domain.users.aggregates import UserAggregate
from domain.users.repositories import IUserRepository
from infrastructure.db.models.users_models import UserModel

try:
    from core.shared.utils.time import utc_now
except ImportError:
    from datetime import timezone

    def utc_now() -> datetime:
        return datetime.now(timezone.utc)


class SQLAlchemyUserRepository(IUserRepository):
    """SQLAlchemy implementation of IUserRepository.

    This is an Adapter in Hexagonal Architecture - it implements
    the Port (IUserRepository) using SQLAlchemy.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: str) -> UserAggregate | None:
        """Get a user by ID."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_aggregate(model)

    async def get_by_email(self, email: str) -> UserAggregate | None:
        """Get a user by email address."""
        stmt = select(UserModel).where(UserModel.email == email.lower())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_aggregate(model)

    async def save(self, user: UserAggregate) -> UserAggregate:
        """Save a user aggregate."""
        # Check if user exists
        existing = await self._session.get(UserModel, user.id)

        if existing:
            # Update existing
            existing.email = user.email
            existing.password_hash = user.password_hash
            existing.username = user.username
            existing.display_name = user.display_name
            existing.is_active = user.is_active
            existing.is_verified = user.is_verified
            existing.updated_at = utc_now()
            existing.last_login_at = user.last_login_at
            existing.version += 1
        else:
            # Create new
            model = UserModel(
                id=user.id,
                email=user.email.lower(),
                password_hash=user.password_hash,
                username=user.username,
                display_name=user.display_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at or utc_now(),
                updated_at=user.updated_at or utc_now(),
                last_login_at=user.last_login_at,
                version=1,
            )
            self._session.add(model)

        await self._session.flush()
        return user

    async def delete(self, user_id: str) -> bool:
        """Delete a user by ID."""
        model = await self._session.get(UserModel, user_id)
        if model is None:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True

    async def exists_by_email(self, email: str) -> bool:
        """Check if a user exists with the given email."""
        stmt = (
            select(func.count())
            .select_from(UserModel)
            .where(UserModel.email == email.lower())
        )
        result = await self._session.execute(stmt)
        count = result.scalar_one()
        return count > 0

    async def list_active(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UserAggregate]:
        """List active users with pagination."""
        stmt = (
            select(UserModel)
            .where(UserModel.is_active)
            .order_by(UserModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_aggregate(m) for m in models]

    async def count_active(self) -> int:
        """Count active users."""
        stmt = select(func.count()).select_from(UserModel).where(UserModel.is_active)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    def _to_aggregate(self, model: UserModel) -> UserAggregate:
        """Convert database model to domain aggregate."""
        return UserAggregate(
            id=model.id,
            email=model.email,
            password_hash=model.password_hash,
            username=model.username,
            display_name=model.display_name,
            is_active=model.is_active,
            is_verified=model.is_verified,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_login_at=model.last_login_at,
        )
