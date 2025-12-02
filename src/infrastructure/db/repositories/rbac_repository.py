"""RBAC Repository for role and permission management.

**Feature: core-rbac-system**
**Part of: Core API (permanent)**
"""

from datetime import datetime, UTC
from uuid import uuid4
import logging

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models.rbac_models import RoleModel, UserRoleModel

logger = logging.getLogger(__name__)


class RBACRepository:
    """Repository for RBAC operations.

    Handles role and user-role persistence.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # === Role Operations ===

    async def get_role_by_name(self, name: str) -> RoleModel | None:
        """Get role by name."""
        stmt = select(RoleModel).where(
            and_(
                RoleModel.name == name,
                RoleModel.is_active == True,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role_by_id(self, role_id: str) -> RoleModel | None:
        """Get role by ID."""
        stmt = select(RoleModel).where(RoleModel.id == role_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_roles(self, include_inactive: bool = False) -> list[RoleModel]:
        """Get all roles."""
        stmt = select(RoleModel)
        if not include_inactive:
            stmt = stmt.where(RoleModel.is_active == True)
        stmt = stmt.order_by(RoleModel.name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_role(
        self,
        name: str,
        description: str,
        permissions: list[str],
        is_system: bool = False,
    ) -> RoleModel:
        """Create a new role."""
        role = RoleModel(
            id=str(uuid4()),
            name=name,
            description=description,
            permissions=permissions,
            is_system=is_system,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._session.add(role)
        await self._session.commit()
        await self._session.refresh(role)
        logger.info(f"Created role: {name}")
        return role

    async def update_role(
        self,
        role_id: str,
        description: str | None = None,
        permissions: list[str] | None = None,
    ) -> RoleModel | None:
        """Update a role."""
        role = await self.get_role_by_id(role_id)
        if not role:
            return None

        if role.is_system:
            logger.warning(f"Attempted to modify system role: {role.name}")
            raise ValueError("Cannot modify system roles")

        if description is not None:
            role.description = description
        if permissions is not None:
            role.permissions = permissions

        role.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(role)
        return role

    # === User Role Operations ===

    async def get_user_roles(self, user_id: str) -> list[RoleModel]:
        """Get all roles for a user."""
        stmt = (
            select(RoleModel)
            .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
            .where(
                and_(
                    UserRoleModel.user_id == user_id,
                    RoleModel.is_active == True,
                )
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_permissions(self, user_id: str) -> set[str]:
        """Get all permissions for a user (from all roles)."""
        roles = await self.get_user_roles(user_id)
        permissions: set[str] = set()
        for role in roles:
            permissions.update(role.permissions or [])
        return permissions

    async def assign_role(
        self,
        user_id: str,
        role_name: str,
        assigned_by: str | None = None,
    ) -> UserRoleModel | None:
        """Assign a role to a user."""
        role = await self.get_role_by_name(role_name)
        if not role:
            logger.warning(f"Role not found: {role_name}")
            return None

        # Check if already assigned
        stmt = select(UserRoleModel).where(
            and_(
                UserRoleModel.user_id == user_id,
                UserRoleModel.role_id == role.id,
            )
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            logger.info(f"Role {role_name} already assigned to user {user_id}")
            return existing

        user_role = UserRoleModel(
            id=str(uuid4()),
            user_id=user_id,
            role_id=role.id,
            assigned_at=datetime.now(UTC),
            assigned_by=assigned_by,
        )
        self._session.add(user_role)
        await self._session.commit()
        await self._session.refresh(user_role)
        logger.info(f"Assigned role {role_name} to user {user_id}")
        return user_role

    async def revoke_role(self, user_id: str, role_name: str) -> bool:
        """Revoke a role from a user."""
        role = await self.get_role_by_name(role_name)
        if not role:
            return False

        stmt = select(UserRoleModel).where(
            and_(
                UserRoleModel.user_id == user_id,
                UserRoleModel.role_id == role.id,
            )
        )
        result = await self._session.execute(stmt)
        user_role = result.scalar_one_or_none()

        if user_role:
            await self._session.delete(user_role)
            await self._session.commit()
            logger.info(f"Revoked role {role_name} from user {user_id}")
            return True
        return False

    async def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has a specific permission."""
        permissions = await self.get_user_permissions(user_id)
        return permission in permissions

    async def has_role(self, user_id: str, role_name: str) -> bool:
        """Check if user has a specific role."""
        roles = await self.get_user_roles(user_id)
        return any(r.name == role_name for r in roles)
