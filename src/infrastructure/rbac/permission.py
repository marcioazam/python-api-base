"""Generic permission with PEP 695 type parameters.

**Feature: enterprise-generics-2025**
**Requirement: R14.1 - Generic_Permission[TResource, TAction]**
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable


# =============================================================================
# Protocols for Type Bounds
# =============================================================================


@runtime_checkable
class Resource(Protocol):
    """Protocol for resource types.

    **Requirement: R14.1 - TResource SHALL be Enum type**
    """

    @property
    def value(self) -> str:
        """Resource identifier."""
        ...


@runtime_checkable
class Action(Protocol):
    """Protocol for action types.

    **Requirement: R14.1 - TAction SHALL be Enum type**
    """

    @property
    def value(self) -> str:
        """Action identifier."""
        ...


# =============================================================================
# Common Enums
# =============================================================================


class StandardResource(str, Enum):
    """Standard resource types."""

    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    DOCUMENT = "document"
    FILE = "file"
    REPORT = "report"
    SETTINGS = "settings"
    API_KEY = "api_key"
    WEBHOOK = "webhook"
    AUDIT_LOG = "audit_log"


class StandardAction(str, Enum):
    """Standard CRUD actions."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    EXPORT = "export"
    IMPORT = "import"
    EXECUTE = "execute"
    APPROVE = "approve"
    REJECT = "reject"


# =============================================================================
# Generic Permission
# =============================================================================


@dataclass(frozen=True, slots=True)
class Permission[TResource: Enum, TAction: Enum]:
    """Generic permission with typed resource and action.

    **Requirement: R14.1 - Generic_Permission[TResource, TAction]**

    Type Parameters:
        TResource: Resource enum type.
        TAction: Action enum type.

    Example:
        ```python
        class MyResource(str, Enum):
            DOCUMENT = "document"
            REPORT = "report"

        class MyAction(str, Enum):
            READ = "read"
            WRITE = "write"

        # Create typed permission
        read_doc = Permission[MyResource, MyAction](
            resource=MyResource.DOCUMENT,
            action=MyAction.READ,
        )
        ```
    """

    resource: TResource
    action: TAction
    conditions: frozenset[str] | None = None

    def __str__(self) -> str:
        """String representation."""
        return f"{self.resource.value}:{self.action.value}"

    def __hash__(self) -> int:
        """Hash for set operations."""
        return hash((self.resource, self.action, self.conditions))

    def matches(self, resource: TResource, action: TAction) -> bool:
        """Check if permission matches resource and action.

        Args:
            resource: Resource to check.
            action: Action to check.

        Returns:
            True if permission matches.
        """
        return self.resource == resource and self.action == action

    def with_condition(self, condition: str) -> "Permission[TResource, TAction]":
        """Create permission with additional condition.

        Args:
            condition: Condition to add (e.g., "own", "department").

        Returns:
            New permission with condition.
        """
        existing = self.conditions or frozenset()
        return Permission(
            resource=self.resource,
            action=self.action,
            conditions=existing | {condition},
        )


# =============================================================================
# Permission Set
# =============================================================================


class PermissionSet[TResource: Enum, TAction: Enum]:
    """Collection of permissions with set operations.

    Type Parameters:
        TResource: Resource enum type.
        TAction: Action enum type.
    """

    def __init__(
        self,
        permissions: set[Permission[TResource, TAction]] | None = None,
    ) -> None:
        """Initialize permission set.

        Args:
            permissions: Initial permissions.
        """
        self._permissions: set[Permission[TResource, TAction]] = permissions or set()

    def add(self, permission: Permission[TResource, TAction]) -> None:
        """Add permission to set."""
        self._permissions.add(permission)

    def remove(self, permission: Permission[TResource, TAction]) -> None:
        """Remove permission from set."""
        self._permissions.discard(permission)

    def has(self, resource: TResource, action: TAction) -> bool:
        """Check if set contains permission.

        Args:
            resource: Resource to check.
            action: Action to check.

        Returns:
            True if permission exists.
        """
        return any(p.matches(resource, action) for p in self._permissions)

    def __contains__(self, permission: Permission[TResource, TAction]) -> bool:
        """Check if permission is in set."""
        return permission in self._permissions

    def __iter__(self):
        """Iterate over permissions."""
        return iter(self._permissions)

    def __len__(self) -> int:
        """Number of permissions."""
        return len(self._permissions)

    def __or__(
        self,
        other: "PermissionSet[TResource, TAction]",
    ) -> "PermissionSet[TResource, TAction]":
        """Union of permission sets."""
        return PermissionSet(self._permissions | other._permissions)

    def __and__(
        self,
        other: "PermissionSet[TResource, TAction]",
    ) -> "PermissionSet[TResource, TAction]":
        """Intersection of permission sets."""
        return PermissionSet(self._permissions & other._permissions)


# =============================================================================
# Permission Factory
# =============================================================================


def create_crud_permissions[TResource: Enum](
    resource: TResource,
) -> PermissionSet[TResource, StandardAction]:
    """Create standard CRUD permissions for resource.

    Args:
        resource: Resource to create permissions for.

    Returns:
        PermissionSet with create, read, update, delete, list permissions.
    """
    return PermissionSet({
        Permission(resource, StandardAction.CREATE),
        Permission(resource, StandardAction.READ),
        Permission(resource, StandardAction.UPDATE),
        Permission(resource, StandardAction.DELETE),
        Permission(resource, StandardAction.LIST),
    })
