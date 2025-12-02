"""Generic role with PEP 695 type parameters.

**Feature: enterprise-generics-2025**
**Requirement: R14.4 - Generic_Role[TPermission]**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from infrastructure.rbac.permission import Permission, PermissionSet


# =============================================================================
# Generic Role
# =============================================================================


@dataclass
class Role[TPermission]:
    """Generic role containing typed permissions.

    **Requirement: R14.4 - Generic_Role[TPermission] contains set of typed permissions**

    Type Parameters:
        TPermission: Permission type this role contains.

    Example:
        ```python
        admin_role = Role[Permission[Resource, Action]](
            name="admin",
            description="Administrator role",
            permissions={
                Permission(Resource.USER, Action.CREATE),
                Permission(Resource.USER, Action.DELETE),
            },
        )
        ```
    """

    name: str
    description: str = ""
    permissions: set[TPermission] = field(default_factory=set)
    parent: "Role[TPermission] | None" = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_permission(self, permission: TPermission) -> bool:
        """Check if role has permission.

        Includes inherited permissions from parent role.

        Args:
            permission: Permission to check.

        Returns:
            True if role has permission.
        """
        if permission in self.permissions:
            return True
        if self.parent:
            return self.parent.has_permission(permission)
        return False

    def add_permission(self, permission: TPermission) -> None:
        """Add permission to role.

        Args:
            permission: Permission to add.
        """
        self.permissions.add(permission)

    def remove_permission(self, permission: TPermission) -> None:
        """Remove permission from role.

        Args:
            permission: Permission to remove.
        """
        self.permissions.discard(permission)

    def get_all_permissions(self) -> set[TPermission]:
        """Get all permissions including inherited.

        Returns:
            Set of all permissions.
        """
        perms = set(self.permissions)
        if self.parent:
            perms |= self.parent.get_all_permissions()
        return perms

    def inherits_from(self, parent: "Role[TPermission]") -> "Role[TPermission]":
        """Set parent role for inheritance.

        Args:
            parent: Parent role to inherit from.

        Returns:
            Self for chaining.
        """
        self.parent = parent
        return self


# =============================================================================
# Role Registry
# =============================================================================


class RoleRegistry[TResource: Enum, TAction: Enum]:
    """Registry for managing roles.

    Type Parameters:
        TResource: Resource enum type.
        TAction: Action enum type.
    """

    def __init__(self) -> None:
        """Initialize registry."""
        self._roles: dict[str, Role[Permission[TResource, TAction]]] = {}

    def register(self, role: Role[Permission[TResource, TAction]]) -> None:
        """Register a role.

        Args:
            role: Role to register.
        """
        self._roles[role.name] = role

    def get(self, name: str) -> Role[Permission[TResource, TAction]] | None:
        """Get role by name.

        Args:
            name: Role name.

        Returns:
            Role or None if not found.
        """
        return self._roles.get(name)

    def get_or_raise(self, name: str) -> Role[Permission[TResource, TAction]]:
        """Get role or raise error.

        Args:
            name: Role name.

        Returns:
            Role.

        Raises:
            KeyError: If role not found.
        """
        if name not in self._roles:
            raise KeyError(f"Role '{name}' not found")
        return self._roles[name]

    def list(self) -> list[Role[Permission[TResource, TAction]]]:
        """List all registered roles.

        Returns:
            List of roles.
        """
        return list(self._roles.values())

    def create_role(
        self,
        name: str,
        permissions: set[Permission[TResource, TAction]],
        description: str = "",
        parent: str | None = None,
    ) -> Role[Permission[TResource, TAction]]:
        """Create and register a new role.

        Args:
            name: Role name.
            permissions: Set of permissions.
            description: Role description.
            parent: Parent role name for inheritance.

        Returns:
            Created role.
        """
        parent_role = self.get(parent) if parent else None
        role = Role(
            name=name,
            description=description,
            permissions=permissions,
            parent=parent_role,
        )
        self.register(role)
        return role


# =============================================================================
# Standard Role Presets
# =============================================================================


def create_standard_roles[TResource: Enum, TAction: Enum](
    registry: RoleRegistry[TResource, TAction],
    resources: list[TResource],
    actions: type[TAction],
) -> None:
    """Create standard roles (admin, editor, viewer) for resources.

    Args:
        registry: Role registry to populate.
        resources: List of resources.
        actions: Action enum class.
    """
    # Get action values
    read_action = getattr(actions, "READ", None)
    list_action = getattr(actions, "LIST", None)
    create_action = getattr(actions, "CREATE", None)
    update_action = getattr(actions, "UPDATE", None)
    delete_action = getattr(actions, "DELETE", None)

    # Viewer - read only
    viewer_perms: set[Permission[TResource, TAction]] = set()
    for resource in resources:
        if read_action:
            viewer_perms.add(Permission(resource, read_action))
        if list_action:
            viewer_perms.add(Permission(resource, list_action))

    registry.create_role(
        name="viewer",
        description="Read-only access",
        permissions=viewer_perms,
    )

    # Editor - CRUD except delete
    editor_perms: set[Permission[TResource, TAction]] = set(viewer_perms)
    for resource in resources:
        if create_action:
            editor_perms.add(Permission(resource, create_action))
        if update_action:
            editor_perms.add(Permission(resource, update_action))

    registry.create_role(
        name="editor",
        description="Create and edit access",
        permissions=editor_perms,
        parent="viewer",
    )

    # Admin - full access
    admin_perms: set[Permission[TResource, TAction]] = set(editor_perms)
    for resource in resources:
        if delete_action:
            admin_perms.add(Permission(resource, delete_action))

    registry.create_role(
        name="admin",
        description="Full access",
        permissions=admin_perms,
        parent="editor",
    )
