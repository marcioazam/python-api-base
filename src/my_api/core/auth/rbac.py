"""Role-Based Access Control (RBAC) service.

**Feature: api-base-improvements**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4**
"""

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Protocol, runtime_checkable
from collections.abc import Callable

from my_api.core.exceptions import AuthorizationError

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """Standard permission types for RBAC."""

    # Basic CRUD permissions
    READ = "read"
    WRITE = "write"
    DELETE = "delete"

    # Administrative permissions
    ADMIN = "admin"
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"

    # Resource-specific permissions
    VIEW_AUDIT = "view_audit"
    EXPORT_DATA = "export_data"


@dataclass(frozen=True, slots=True)
class Role:
    """Role definition with associated permissions.

    Attributes:
        name: Unique role identifier.
        permissions: Set of permissions granted by this role.
        description: Human-readable role description.
    """

    name: str
    permissions: frozenset[Permission] = field(default_factory=frozenset)
    description: str = ""

    def has_permission(self, permission: Permission) -> bool:
        """Check if role has a specific permission."""
        return permission in self.permissions

    def to_dict(self) -> dict[str, Any]:
        """Convert role to dictionary."""
        return {
            "name": self.name,
            "permissions": [p.value for p in self.permissions],
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Role":
        """Create role from dictionary."""
        return cls(
            name=data["name"],
            permissions=frozenset(Permission(p) for p in data.get("permissions", [])),
            description=data.get("description", ""),
        )


# Predefined roles
ROLE_ADMIN = Role(
    name="admin",
    permissions=frozenset(Permission),  # All permissions
    description="Full system administrator",
)

ROLE_USER = Role(
    name="user",
    permissions=frozenset([Permission.READ, Permission.WRITE]),
    description="Standard user with read/write access",
)

ROLE_VIEWER = Role(
    name="viewer",
    permissions=frozenset([Permission.READ]),
    description="Read-only access",
)

ROLE_MODERATOR = Role(
    name="moderator",
    permissions=frozenset([
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
        Permission.VIEW_AUDIT,
    ]),
    description="Content moderator",
)


@runtime_checkable
class UserProtocol(Protocol):
    """Protocol for user objects in RBAC context."""

    @property
    def id(self) -> str:
        """User identifier."""
        ...

    @property
    def roles(self) -> list[str]:
        """List of role names assigned to user."""
        ...


@dataclass
class RBACUser:
    """Simple user implementation for RBAC.

    Attributes:
        id: User identifier.
        roles: List of role names.
        scopes: Additional OAuth2-style scopes.
    """

    id: str
    roles: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)


class RBACService:
    """Service for role-based access control.

    Handles permission checking, role management, and
    authorization decisions.
    """

    def __init__(self, roles: dict[str, Role] | None = None) -> None:
        """Initialize RBAC service.

        Args:
            roles: Dictionary of role name to Role objects.
                   If None, uses predefined roles.
        """
        self._roles: dict[str, Role] = roles or {
            ROLE_ADMIN.name: ROLE_ADMIN,
            ROLE_USER.name: ROLE_USER,
            ROLE_VIEWER.name: ROLE_VIEWER,
            ROLE_MODERATOR.name: ROLE_MODERATOR,
        }

    def get_role(self, role_name: str) -> Role | None:
        """Get a role by name.

        Args:
            role_name: Name of the role.

        Returns:
            Role if found, None otherwise.
        """
        return self._roles.get(role_name)

    def add_role(self, role: Role) -> None:
        """Add or update a role.

        Args:
            role: Role to add.
        """
        self._roles[role.name] = role
        logger.debug(f"Added role: {role.name}")

    def get_user_permissions(self, user: UserProtocol | RBACUser) -> set[Permission]:
        """Get all permissions for a user from their roles.

        Combines permissions from all assigned roles.

        Args:
            user: User object with roles attribute.

        Returns:
            Set of all permissions the user has.
        """
        permissions: set[Permission] = set()

        for role_name in user.roles:
            role = self._roles.get(role_name)
            if role:
                permissions.update(role.permissions)

        # Add scope-based permissions if user has scopes
        if hasattr(user, "scopes"):
            for scope in user.scopes:
                try:
                    permissions.add(Permission(scope))
                except ValueError:
                    pass  # Ignore invalid scopes

        return permissions

    def check_permission(
        self,
        user: UserProtocol | RBACUser,
        required: Permission,
    ) -> bool:
        """Check if user has a specific permission.

        Args:
            user: User to check.
            required: Permission required.

        Returns:
            True if user has permission, False otherwise.
        """
        permissions = self.get_user_permissions(user)
        has_permission = required in permissions

        if not has_permission:
            logger.debug(
                f"Permission denied: user={user.id}, "
                f"required={required.value}, "
                f"has={[p.value for p in permissions]}"
            )

        return has_permission

    def check_any_permission(
        self,
        user: UserProtocol | RBACUser,
        required: list[Permission],
    ) -> bool:
        """Check if user has any of the specified permissions.

        Args:
            user: User to check.
            required: List of permissions (any one is sufficient).

        Returns:
            True if user has at least one permission.
        """
        permissions = self.get_user_permissions(user)
        return bool(permissions & set(required))

    def check_all_permissions(
        self,
        user: UserProtocol | RBACUser,
        required: list[Permission],
    ) -> bool:
        """Check if user has all specified permissions.

        Args:
            user: User to check.
            required: List of permissions (all required).

        Returns:
            True if user has all permissions.
        """
        permissions = self.get_user_permissions(user)
        return set(required).issubset(permissions)

    def require_permission(
        self,
        user: UserProtocol | RBACUser,
        required: Permission,
    ) -> None:
        """Require a permission, raising error if not present.

        Args:
            user: User to check.
            required: Permission required.

        Raises:
            AuthorizationError: If user lacks permission.
        """
        if not self.check_permission(user, required):
            logger.warning(
                f"Authorization failed: user={user.id}, "
                f"required={required.value}"
            )
            raise AuthorizationError(
                message=f"Permission '{required.value}' required",
                required_permission=required.value,
            )


# Global RBAC service instance with thread-safe initialization
_rbac_service: RBACService | None = None
_rbac_lock = threading.Lock()


def get_rbac_service() -> RBACService:
    """Get the global RBAC service instance (thread-safe).
    
    Uses double-check locking pattern for thread-safe lazy initialization.
    
    **Feature: core-improvements-v2**
    **Validates: Requirements 1.1, 1.4, 1.5**
    """
    global _rbac_service
    if _rbac_service is None:
        with _rbac_lock:
            if _rbac_service is None:  # Double-check locking
                _rbac_service = RBACService()
    return _rbac_service


def require_permission[F: Callable[..., Any]](*permissions: Permission) -> Callable[[F], F]:
    """Decorator to require permissions on a function/endpoint.

    Can be used with FastAPI dependencies or standalone functions.

    Args:
        *permissions: One or more permissions required (all must be present).

    Returns:
        Decorator function.

    Example:
        @require_permission(Permission.READ, Permission.WRITE)
        async def update_item(item_id: str, user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Look for user in kwargs
            user = kwargs.get("user") or kwargs.get("current_user")
            if user is None:
                raise AuthorizationError(
                    message="Authentication required",
                    required_permission=permissions[0].value if permissions else None,
                )

            rbac = get_rbac_service()
            for perm in permissions:
                rbac.require_permission(user, perm)

            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            user = kwargs.get("user") or kwargs.get("current_user")
            if user is None:
                raise AuthorizationError(
                    message="Authentication required",
                    required_permission=permissions[0].value if permissions else None,
                )

            rbac = get_rbac_service()
            for perm in permissions:
                rbac.require_permission(user, perm)

            return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator
