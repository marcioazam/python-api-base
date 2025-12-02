"""Generic RBAC checker with PEP 695 type parameters.

**Feature: enterprise-generics-2025**
**Requirement: R14.2, R14.3 - Generic_RBAC[TUser] and @requires decorator**
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Protocol, TypeVar, runtime_checkable

from fastapi import HTTPException, Request
from pydantic import BaseModel

from infrastructure.rbac.permission import Permission
from infrastructure.rbac.role import Role, RoleRegistry

logger = logging.getLogger(__name__)


# =============================================================================
# User Protocol
# =============================================================================


@runtime_checkable
class RBACUser(Protocol):
    """Protocol for users with RBAC support.

    Users must have roles for RBAC checking.
    """

    @property
    def roles(self) -> list[str]:
        """List of role names assigned to user."""
        ...


# =============================================================================
# RBAC Checker
# =============================================================================


class RBAC[TUser: RBACUser, TResource: Enum, TAction: Enum]:
    """Generic RBAC permission checker.

    **Requirement: R14.2 - Generic_RBAC[TUser].has_permission()**

    Type Parameters:
        TUser: User type implementing RBACUser protocol.
        TResource: Resource enum type.
        TAction: Action enum type.

    Example:
        ```python
        class User(BaseModel):
            id: str
            roles: list[str]

        rbac = RBAC[User, Resource, Action](role_registry)

        if rbac.has_permission(user, Permission(Resource.DOC, Action.READ)):
            # Allow access
            ...
        ```
    """

    def __init__(
        self,
        role_registry: RoleRegistry[TResource, TAction],
        audit_logger: Callable[[Any], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize RBAC checker.

        Args:
            role_registry: Registry of roles and permissions.
            audit_logger: Optional async audit logger callback.
        """
        self._registry = role_registry
        self._audit_logger = audit_logger

    def has_permission(
        self,
        user: TUser,
        permission: Permission[TResource, TAction],
    ) -> bool:
        """Check if user has permission.

        **Requirement: R14.2 - has_permission() returns bool**

        Args:
            user: User to check.
            permission: Permission to check for.

        Returns:
            True if user has permission.
        """
        for role_name in user.roles:
            role = self._registry.get(role_name)
            if role and role.has_permission(permission):
                return True
        return False

    def check_permission(
        self,
        user: TUser,
        resource: TResource,
        action: TAction,
    ) -> bool:
        """Check permission by resource and action.

        Args:
            user: User to check.
            resource: Resource type.
            action: Action type.

        Returns:
            True if user has permission.
        """
        permission = Permission(resource, action)
        return self.has_permission(user, permission)

    def get_user_permissions(
        self,
        user: TUser,
    ) -> set[Permission[TResource, TAction]]:
        """Get all permissions for user.

        Args:
            user: User to get permissions for.

        Returns:
            Set of all user permissions.
        """
        permissions: set[Permission[TResource, TAction]] = set()
        for role_name in user.roles:
            role = self._registry.get(role_name)
            if role:
                permissions |= role.get_all_permissions()
        return permissions

    async def require_permission(
        self,
        user: TUser,
        permission: Permission[TResource, TAction],
        resource_id: str | None = None,
    ) -> None:
        """Require permission or raise exception.

        Args:
            user: User to check.
            permission: Required permission.
            resource_id: Optional resource ID for audit.

        Raises:
            PermissionDenied: If user lacks permission.
        """
        if not self.has_permission(user, permission):
            if self._audit_logger:
                await self._audit_logger({
                    "user": user,
                    "permission": str(permission),
                    "resource_id": resource_id,
                    "granted": False,
                })
            raise PermissionDenied(
                user=user,
                permission=permission,
                resource_id=resource_id,
            )

        if self._audit_logger:
            await self._audit_logger({
                "user": user,
                "permission": str(permission),
                "resource_id": resource_id,
                "granted": True,
            })


# =============================================================================
# Exceptions
# =============================================================================


class PermissionDenied[TUser, TResource: Enum, TAction: Enum](Exception):
    """Permission denied exception with typed context."""

    def __init__(
        self,
        user: TUser,
        permission: Permission[TResource, TAction],
        resource_id: str | None = None,
        message: str | None = None,
    ) -> None:
        self.user = user
        self.permission = permission
        self.resource_id = resource_id
        super().__init__(
            message or f"Permission denied: {permission} for resource {resource_id}"
        )


# =============================================================================
# Decorator
# =============================================================================


def requires[TResource: Enum, TAction: Enum](
    permission: Permission[TResource, TAction],
    user_attr: str = "current_user",
    rbac_attr: str = "rbac",
) -> Callable:
    """Decorator to require permission for route.

    **Requirement: R14.3 - @requires[TResource, TAction](permission) decorator**

    Type Parameters:
        TResource: Resource enum type.
        TAction: Action enum type.

    Args:
        permission: Required permission.
        user_attr: Request state attribute for user.
        rbac_attr: Request state attribute for RBAC checker.

    Returns:
        Route decorator.

    Example:
        ```python
        @app.get("/documents/{id}")
        @requires(Permission(Resource.DOCUMENT, Action.READ))
        async def get_document(id: str, request: Request):
            ...
        ```
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Find request in args
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            for value in kwargs.values():
                if isinstance(value, Request):
                    request = value
                    break

            if request is None:
                raise HTTPException(
                    status_code=500,
                    detail="Request not found in handler arguments",
                )

            # Get user and RBAC from request state
            user = getattr(request.state, user_attr, None)
            if user is None:
                raise HTTPException(
                    status_code=401,
                    detail="User not authenticated",
                )

            rbac = getattr(request.state, rbac_attr, None)
            if rbac is None:
                # Fallback: check user roles directly
                if hasattr(user, "roles"):
                    # Simple role check without registry
                    has_perm = _check_permission_simple(user, permission)
                    if not has_perm:
                        raise HTTPException(
                            status_code=403,
                            detail=f"Permission denied: {permission}",
                        )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail="RBAC not configured",
                    )
            else:
                if not rbac.has_permission(user, permission):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permission denied: {permission}",
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def _check_permission_simple[TResource: Enum, TAction: Enum](
    user: Any,
    permission: Permission[TResource, TAction],
) -> bool:
    """Simple permission check without registry.

    Maps permission to role naming convention.
    """
    perm_str = str(permission).lower()

    # Check if any role grants this permission
    # Convention: role name contains permission
    for role in user.roles:
        role_lower = role.lower()
        if role_lower == "admin":
            return True
        if perm_str in role_lower:
            return True
        # Check action-based: "editor" can create/update
        if "editor" in role_lower and permission.action.value in ("create", "update"):
            return True
        if "viewer" in role_lower and permission.action.value in ("read", "list"):
            return True

    return False
