"""Tests for RBAC checker module.

Tests for RBAC, PermissionDeniedError, and helper functions.
"""

from enum import Enum
from unittest.mock import AsyncMock, MagicMock

import pytest

from infrastructure.rbac.checker import (
    RBAC,
    PermissionDeniedError,
    RBACUser,
    _check_permission_simple,
)
from infrastructure.rbac.permission import Permission
from infrastructure.rbac.role import Role, RoleRegistry


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


class MockUser:
    """Mock user implementing RBACUser protocol."""

    def __init__(self, roles: list[str]) -> None:
        self._roles = roles

    @property
    def roles(self) -> list[str]:
        return self._roles


class TestRBACUserProtocol:
    """Tests for RBACUser protocol."""

    def test_mock_user_is_rbac_user(self) -> None:
        """MockUser should implement RBACUser protocol."""
        user = MockUser(roles=["admin"])
        assert isinstance(user, RBACUser)

    def test_user_without_roles_not_rbac_user(self) -> None:
        """Object without roles should not be RBACUser."""

        class NoRolesUser:
            pass

        user = NoRolesUser()
        assert not isinstance(user, RBACUser)


class TestRBAC:
    """Tests for RBAC class."""

    @pytest.fixture
    def registry(self) -> RoleRegistry[Resource, Action]:
        """Create test role registry."""
        registry: RoleRegistry[Resource, Action] = RoleRegistry()
        read_perm = Permission(Resource.USER, Action.READ)
        create_perm = Permission(Resource.USER, Action.CREATE)
        delete_perm = Permission(Resource.USER, Action.DELETE)

        registry.create_role("viewer", permissions={read_perm})
        registry.create_role("editor", permissions={read_perm, create_perm})
        registry.create_role("admin", permissions={read_perm, create_perm, delete_perm})
        return registry

    @pytest.fixture
    def rbac(
        self, registry: RoleRegistry[Resource, Action]
    ) -> RBAC[MockUser, Resource, Action]:
        """Create test RBAC checker."""
        return RBAC(registry)

    def test_has_permission_with_role(
        self, rbac: RBAC[MockUser, Resource, Action]
    ) -> None:
        """has_permission should return True when user has permission."""
        user = MockUser(roles=["viewer"])
        perm = Permission(Resource.USER, Action.READ)
        assert rbac.has_permission(user, perm) is True

    def test_has_permission_without_role(
        self, rbac: RBAC[MockUser, Resource, Action]
    ) -> None:
        """has_permission should return False when user lacks permission."""
        user = MockUser(roles=["viewer"])
        perm = Permission(Resource.USER, Action.DELETE)
        assert rbac.has_permission(user, perm) is False

    def test_has_permission_no_roles(
        self, rbac: RBAC[MockUser, Resource, Action]
    ) -> None:
        """has_permission should return False for user with no roles."""
        user = MockUser(roles=[])
        perm = Permission(Resource.USER, Action.READ)
        assert rbac.has_permission(user, perm) is False

    def test_has_permission_unknown_role(
        self, rbac: RBAC[MockUser, Resource, Action]
    ) -> None:
        """has_permission should return False for unknown role."""
        user = MockUser(roles=["unknown_role"])
        perm = Permission(Resource.USER, Action.READ)
        assert rbac.has_permission(user, perm) is False

    def test_has_permission_multiple_roles(
        self, rbac: RBAC[MockUser, Resource, Action]
    ) -> None:
        """has_permission should check all user roles."""
        user = MockUser(roles=["viewer", "admin"])
        perm = Permission(Resource.USER, Action.DELETE)
        assert rbac.has_permission(user, perm) is True

    def test_check_permission(self, rbac: RBAC[MockUser, Resource, Action]) -> None:
        """check_permission should work with resource and action."""
        user = MockUser(roles=["viewer"])
        assert rbac.check_permission(user, Resource.USER, Action.READ) is True
        assert rbac.check_permission(user, Resource.USER, Action.DELETE) is False

    def test_get_user_permissions(
        self, rbac: RBAC[MockUser, Resource, Action]
    ) -> None:
        """get_user_permissions should return all permissions."""
        user = MockUser(roles=["viewer"])
        perms = rbac.get_user_permissions(user)
        assert Permission(Resource.USER, Action.READ) in perms

    def test_get_user_permissions_multiple_roles(
        self, rbac: RBAC[MockUser, Resource, Action]
    ) -> None:
        """get_user_permissions should combine permissions from all roles."""
        user = MockUser(roles=["viewer", "editor"])
        perms = rbac.get_user_permissions(user)
        assert Permission(Resource.USER, Action.READ) in perms
        assert Permission(Resource.USER, Action.CREATE) in perms

    def test_get_user_permissions_no_roles(
        self, rbac: RBAC[MockUser, Resource, Action]
    ) -> None:
        """get_user_permissions should return empty set for no roles."""
        user = MockUser(roles=[])
        perms = rbac.get_user_permissions(user)
        assert perms == set()

    @pytest.mark.asyncio
    async def test_require_permission_granted(
        self, rbac: RBAC[MockUser, Resource, Action]
    ) -> None:
        """require_permission should not raise when permission granted."""
        user = MockUser(roles=["viewer"])
        perm = Permission(Resource.USER, Action.READ)
        await rbac.require_permission(user, perm)  # Should not raise

    @pytest.mark.asyncio
    async def test_require_permission_denied(
        self, rbac: RBAC[MockUser, Resource, Action]
    ) -> None:
        """require_permission should raise when permission denied."""
        user = MockUser(roles=["viewer"])
        perm = Permission(Resource.USER, Action.DELETE)
        with pytest.raises(PermissionDeniedError):
            await rbac.require_permission(user, perm)

    @pytest.mark.asyncio
    async def test_require_permission_with_audit_logger(
        self, registry: RoleRegistry[Resource, Action]
    ) -> None:
        """require_permission should call audit logger."""
        audit_logger = AsyncMock()
        rbac: RBAC[MockUser, Resource, Action] = RBAC(registry, audit_logger)
        user = MockUser(roles=["viewer"])
        perm = Permission(Resource.USER, Action.READ)

        await rbac.require_permission(user, perm, resource_id="123")

        audit_logger.assert_called_once()
        call_args = audit_logger.call_args[0][0]
        assert call_args["granted"] is True
        assert call_args["resource_id"] == "123"

    @pytest.mark.asyncio
    async def test_require_permission_denied_with_audit(
        self, registry: RoleRegistry[Resource, Action]
    ) -> None:
        """require_permission should audit denied access."""
        audit_logger = AsyncMock()
        rbac: RBAC[MockUser, Resource, Action] = RBAC(registry, audit_logger)
        user = MockUser(roles=["viewer"])
        perm = Permission(Resource.USER, Action.DELETE)

        with pytest.raises(PermissionDeniedError):
            await rbac.require_permission(user, perm)

        audit_logger.assert_called_once()
        call_args = audit_logger.call_args[0][0]
        assert call_args["granted"] is False


class TestPermissionDeniedError:
    """Tests for PermissionDeniedError exception."""

    def test_init_stores_user(self) -> None:
        """Error should store user."""
        user = MockUser(roles=["viewer"])
        perm = Permission(Resource.USER, Action.DELETE)
        error = PermissionDeniedError(user, perm)
        assert error.user == user

    def test_init_stores_permission(self) -> None:
        """Error should store permission."""
        user = MockUser(roles=["viewer"])
        perm = Permission(Resource.USER, Action.DELETE)
        error = PermissionDeniedError(user, perm)
        assert error.permission == perm

    def test_init_stores_resource_id(self) -> None:
        """Error should store resource_id."""
        user = MockUser(roles=["viewer"])
        perm = Permission(Resource.USER, Action.DELETE)
        error = PermissionDeniedError(user, perm, resource_id="123")
        assert error.resource_id == "123"

    def test_default_message(self) -> None:
        """Error should have default message."""
        user = MockUser(roles=["viewer"])
        perm = Permission(Resource.USER, Action.DELETE)
        error = PermissionDeniedError(user, perm, resource_id="123")
        assert "Permission denied" in str(error)

    def test_custom_message(self) -> None:
        """Error should accept custom message."""
        user = MockUser(roles=["viewer"])
        perm = Permission(Resource.USER, Action.DELETE)
        error = PermissionDeniedError(user, perm, message="Custom error")
        assert str(error) == "Custom error"


class TestCheckPermissionSimple:
    """Tests for _check_permission_simple function."""

    def test_admin_has_all_permissions(self) -> None:
        """Admin role should have all permissions."""
        user = MockUser(roles=["admin"])
        perm = Permission(Resource.USER, Action.DELETE)
        assert _check_permission_simple(user, perm) is True

    def test_viewer_has_read_permission(self) -> None:
        """Viewer role should have read permission."""
        user = MockUser(roles=["viewer"])
        perm = Permission(Resource.USER, Action.READ)
        assert _check_permission_simple(user, perm) is True

    def test_viewer_has_list_permission(self) -> None:
        """Viewer role should have list permission."""
        user = MockUser(roles=["viewer"])
        perm = Permission(Resource.USER, Action.LIST)
        assert _check_permission_simple(user, perm) is True

    def test_editor_has_create_permission(self) -> None:
        """Editor role should have create permission."""
        user = MockUser(roles=["editor"])
        perm = Permission(Resource.USER, Action.CREATE)
        assert _check_permission_simple(user, perm) is True

    def test_editor_has_update_permission(self) -> None:
        """Editor role should have update permission."""
        user = MockUser(roles=["editor"])
        perm = Permission(Resource.USER, Action.UPDATE)
        assert _check_permission_simple(user, perm) is True

    def test_no_permission_for_unknown_role(self) -> None:
        """Unknown role should not have permissions."""
        user = MockUser(roles=["unknown"])
        perm = Permission(Resource.USER, Action.DELETE)
        assert _check_permission_simple(user, perm) is False
