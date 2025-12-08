"""Tests for RBAC role module.

Tests for Role, RoleRegistry, and create_standard_roles.
"""

from enum import Enum

import pytest

from infrastructure.rbac.permission import Permission
from infrastructure.rbac.role import Role, RoleRegistry, create_standard_roles


class Resource(Enum):
    """Test resource enum."""

    USER = "user"
    POST = "post"
    COMMENT = "comment"


class Action(Enum):
    """Test action enum."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"


class TestRole:
    """Tests for Role class."""

    def test_init_with_name(self) -> None:
        """Role should store name."""
        role: Role[Permission[Resource, Action]] = Role(name="admin")
        assert role.name == "admin"

    def test_init_default_description(self) -> None:
        """Role should have empty description by default."""
        role: Role[Permission[Resource, Action]] = Role(name="test")
        assert role.description == ""

    def test_init_with_description(self) -> None:
        """Role should store description."""
        role: Role[Permission[Resource, Action]] = Role(
            name="admin", description="Administrator"
        )
        assert role.description == "Administrator"

    def test_init_default_permissions(self) -> None:
        """Role should have empty permissions by default."""
        role: Role[Permission[Resource, Action]] = Role(name="test")
        assert role.permissions == set()

    def test_init_with_permissions(self) -> None:
        """Role should store permissions."""
        perm = Permission(Resource.USER, Action.READ)
        role: Role[Permission[Resource, Action]] = Role(
            name="viewer", permissions={perm}
        )
        assert perm in role.permissions

    def test_has_permission_direct(self) -> None:
        """has_permission should return True for direct permission."""
        perm = Permission(Resource.USER, Action.READ)
        role: Role[Permission[Resource, Action]] = Role(
            name="viewer", permissions={perm}
        )
        assert role.has_permission(perm) is True

    def test_has_permission_missing(self) -> None:
        """has_permission should return False for missing permission."""
        role: Role[Permission[Resource, Action]] = Role(name="empty")
        perm = Permission(Resource.USER, Action.DELETE)
        assert role.has_permission(perm) is False

    def test_has_permission_inherited(self) -> None:
        """has_permission should check parent role."""
        parent_perm = Permission(Resource.USER, Action.READ)
        parent: Role[Permission[Resource, Action]] = Role(
            name="parent", permissions={parent_perm}
        )
        child: Role[Permission[Resource, Action]] = Role(name="child", parent=parent)
        assert child.has_permission(parent_perm) is True

    def test_add_permission(self) -> None:
        """add_permission should add permission to role."""
        role: Role[Permission[Resource, Action]] = Role(name="test")
        perm = Permission(Resource.USER, Action.CREATE)
        role.add_permission(perm)
        assert perm in role.permissions

    def test_remove_permission(self) -> None:
        """remove_permission should remove permission from role."""
        perm = Permission(Resource.USER, Action.READ)
        role: Role[Permission[Resource, Action]] = Role(
            name="test", permissions={perm}
        )
        role.remove_permission(perm)
        assert perm not in role.permissions

    def test_remove_permission_not_present(self) -> None:
        """remove_permission should not raise for missing permission."""
        role: Role[Permission[Resource, Action]] = Role(name="test")
        perm = Permission(Resource.USER, Action.DELETE)
        role.remove_permission(perm)  # Should not raise

    def test_get_all_permissions_direct(self) -> None:
        """get_all_permissions should return direct permissions."""
        perm = Permission(Resource.USER, Action.READ)
        role: Role[Permission[Resource, Action]] = Role(
            name="test", permissions={perm}
        )
        assert perm in role.get_all_permissions()

    def test_get_all_permissions_inherited(self) -> None:
        """get_all_permissions should include inherited permissions."""
        parent_perm = Permission(Resource.USER, Action.READ)
        child_perm = Permission(Resource.USER, Action.CREATE)
        parent: Role[Permission[Resource, Action]] = Role(
            name="parent", permissions={parent_perm}
        )
        child: Role[Permission[Resource, Action]] = Role(
            name="child", permissions={child_perm}, parent=parent
        )
        all_perms = child.get_all_permissions()
        assert parent_perm in all_perms
        assert child_perm in all_perms

    def test_inherits_from(self) -> None:
        """inherits_from should set parent and return self."""
        parent: Role[Permission[Resource, Action]] = Role(name="parent")
        child: Role[Permission[Resource, Action]] = Role(name="child")
        result = child.inherits_from(parent)
        assert child.parent == parent
        assert result is child


class TestRoleRegistry:
    """Tests for RoleRegistry class."""

    def test_init_empty(self) -> None:
        """Registry should start empty."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        assert registry.list() == []

    def test_register_role(self) -> None:
        """register should add role to registry."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        role: Role[Permission[Resource, Action]] = Role(name="admin")
        registry.register(role)
        assert registry.get("admin") == role

    def test_get_existing_role(self) -> None:
        """get should return role by name."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        role: Role[Permission[Resource, Action]] = Role(name="viewer")
        registry.register(role)
        assert registry.get("viewer") == role

    def test_get_missing_role(self) -> None:
        """get should return None for missing role."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        assert registry.get("nonexistent") is None

    def test_get_or_raise_existing(self) -> None:
        """get_or_raise should return existing role."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        role: Role[Permission[Resource, Action]] = Role(name="admin")
        registry.register(role)
        assert registry.get_or_raise("admin") == role

    def test_get_or_raise_missing(self) -> None:
        """get_or_raise should raise KeyError for missing role."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        with pytest.raises(KeyError, match="Role 'missing' not found"):
            registry.get_or_raise("missing")

    def test_list_roles(self) -> None:
        """list should return all registered roles."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        role1: Role[Permission[Resource, Action]] = Role(name="admin")
        role2: Role[Permission[Resource, Action]] = Role(name="viewer")
        registry.register(role1)
        registry.register(role2)
        roles = registry.list()
        assert len(roles) == 2
        assert role1 in roles
        assert role2 in roles

    def test_create_role(self) -> None:
        """create_role should create and register role."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        perm = Permission(Resource.USER, Action.READ)
        role = registry.create_role(
            name="viewer",
            permissions={perm},
            description="Read-only",
        )
        assert role.name == "viewer"
        assert role.description == "Read-only"
        assert perm in role.permissions
        assert registry.get("viewer") == role

    def test_create_role_with_parent(self) -> None:
        """create_role should set parent role."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        parent: Role[Permission[Resource, Action]] = Role(name="viewer")
        registry.register(parent)
        child = registry.create_role(
            name="editor",
            permissions=set(),
            parent="viewer",
        )
        assert child.parent == parent


class TestCreateStandardRoles:
    """Tests for create_standard_roles function."""

    def test_creates_viewer_role(self) -> None:
        """Should create viewer role with read permissions."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        create_standard_roles(registry, [Resource.USER], Action)
        viewer = registry.get("viewer")
        assert viewer is not None
        assert viewer.description == "Read-only access"

    def test_creates_editor_role(self) -> None:
        """Should create editor role with CRUD except delete."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        create_standard_roles(registry, [Resource.USER], Action)
        editor = registry.get("editor")
        assert editor is not None
        assert editor.description == "Create and edit access"

    def test_creates_admin_role(self) -> None:
        """Should create admin role with full access."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        create_standard_roles(registry, [Resource.USER], Action)
        admin = registry.get("admin")
        assert admin is not None
        assert admin.description == "Full access"

    def test_viewer_has_read_permission(self) -> None:
        """Viewer should have READ permission."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        create_standard_roles(registry, [Resource.USER], Action)
        viewer = registry.get("viewer")
        assert viewer is not None
        read_perm = Permission(Resource.USER, Action.READ)
        assert viewer.has_permission(read_perm)

    def test_editor_inherits_from_viewer(self) -> None:
        """Editor should inherit from viewer."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        create_standard_roles(registry, [Resource.USER], Action)
        editor = registry.get("editor")
        viewer = registry.get("viewer")
        assert editor is not None
        assert editor.parent == viewer

    def test_admin_inherits_from_editor(self) -> None:
        """Admin should inherit from editor."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        create_standard_roles(registry, [Resource.USER], Action)
        admin = registry.get("admin")
        editor = registry.get("editor")
        assert admin is not None
        assert admin.parent == editor

    def test_admin_has_delete_permission(self) -> None:
        """Admin should have DELETE permission."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        create_standard_roles(registry, [Resource.USER], Action)
        admin = registry.get("admin")
        assert admin is not None
        delete_perm = Permission(Resource.USER, Action.DELETE)
        assert admin.has_permission(delete_perm)
