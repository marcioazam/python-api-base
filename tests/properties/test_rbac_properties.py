"""Property-based tests for RBAC service.

**Feature: api-base-improvements**
**Validates: Requirements 2.1, 2.3**
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.core.auth.rbac import (
    Permission,
    RBACService,
    RBACUser,
    Role,
    ROLE_ADMIN,
    ROLE_USER,
    ROLE_VIEWER,
    ROLE_MODERATOR,
)
from my_app.core.exceptions import AuthorizationError


# Strategy for generating user IDs
user_id_strategy = st.text(
    min_size=1,
    max_size=26,
    alphabet=st.characters(whitelist_categories=("L", "N")),
).filter(lambda x: x.strip() != "")

# Strategy for generating role names
role_name_strategy = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(whitelist_categories=("L",), whitelist_characters="_-"),
).filter(lambda x: x.strip() != "")

# Strategy for generating permission sets
permission_strategy = st.sampled_from(list(Permission))
permission_set_strategy = st.frozensets(permission_strategy, min_size=0, max_size=len(Permission))


class TestInsufficientPermissions:
    """Property tests for insufficient permissions handling."""

    @settings(max_examples=100, deadline=None)
    @given(
        user_id=user_id_strategy,
        required_permission=permission_strategy,
    )
    def test_user_without_permission_raises_403(
        self, user_id: str, required_permission: Permission
    ) -> None:
        """
        **Feature: api-base-improvements, Property 7: Insufficient permissions return 403**
        **Validates: Requirements 2.1**

        For any user without required permission accessing a protected endpoint,
        the response SHALL be 403 Forbidden.
        """
        # Create user with no roles (no permissions)
        user = RBACUser(id=user_id, roles=[])
        service = RBACService()

        # User should not have the permission
        has_permission = service.check_permission(user, required_permission)
        assert not has_permission, "User with no roles should have no permissions"

        # Requiring permission should raise AuthorizationError (403)
        with pytest.raises(AuthorizationError) as exc_info:
            service.require_permission(user, required_permission)

        assert exc_info.value.status_code == 403

    @settings(max_examples=100, deadline=None)
    @given(user_id=user_id_strategy)
    def test_viewer_cannot_write(self, user_id: str) -> None:
        """
        **Feature: api-base-improvements, Property 7: Insufficient permissions return 403**
        **Validates: Requirements 2.1**

        A viewer role user SHALL NOT have write permission.
        """
        user = RBACUser(id=user_id, roles=["viewer"])
        service = RBACService()

        # Viewer should have READ but not WRITE
        assert service.check_permission(user, Permission.READ)
        assert not service.check_permission(user, Permission.WRITE)

        with pytest.raises(AuthorizationError):
            service.require_permission(user, Permission.WRITE)

    @settings(max_examples=50, deadline=None)
    @given(user_id=user_id_strategy)
    def test_user_cannot_admin(self, user_id: str) -> None:
        """
        **Feature: api-base-improvements, Property 7: Insufficient permissions return 403**
        **Validates: Requirements 2.1**

        A standard user role SHALL NOT have admin permission.
        """
        user = RBACUser(id=user_id, roles=["user"])
        service = RBACService()

        assert not service.check_permission(user, Permission.ADMIN)

        with pytest.raises(AuthorizationError):
            service.require_permission(user, Permission.ADMIN)

    @settings(max_examples=50, deadline=None)
    @given(user_id=user_id_strategy, role_name=role_name_strategy)
    def test_unknown_role_grants_no_permissions(
        self, user_id: str, role_name: str
    ) -> None:
        """
        **Feature: api-base-improvements, Property 7: Insufficient permissions return 403**
        **Validates: Requirements 2.1**

        A user with an unknown role SHALL have no permissions.
        """
        # Use a role name that doesn't exist in the service
        unknown_role = f"unknown_{role_name}"
        user = RBACUser(id=user_id, roles=[unknown_role])
        service = RBACService()

        permissions = service.get_user_permissions(user)
        assert len(permissions) == 0, "Unknown role should grant no permissions"


class TestRolePermissionCombination:
    """Property tests for multiple role permission combination."""

    @settings(max_examples=100, deadline=None)
    @given(user_id=user_id_strategy)
    def test_multiple_roles_combine_permissions(self, user_id: str) -> None:
        """
        **Feature: api-base-improvements, Property 8: Multiple roles combine permissions**
        **Validates: Requirements 2.3**

        For any user with multiple roles, the effective permissions SHALL be
        the union of all role permissions.
        """
        # User with both viewer and user roles
        user = RBACUser(id=user_id, roles=["viewer", "user"])
        service = RBACService()

        # Get combined permissions
        permissions = service.get_user_permissions(user)

        # Should have union of viewer (READ) and user (READ, WRITE)
        expected = ROLE_VIEWER.permissions | ROLE_USER.permissions
        assert permissions == expected

    @settings(max_examples=100, deadline=None)
    @given(
        user_id=user_id_strategy,
        permissions1=permission_set_strategy,
        permissions2=permission_set_strategy,
    )
    def test_custom_roles_combine_correctly(
        self,
        user_id: str,
        permissions1: frozenset[Permission],
        permissions2: frozenset[Permission],
    ) -> None:
        """
        **Feature: api-base-improvements, Property 8: Multiple roles combine permissions**
        **Validates: Requirements 2.3**

        For any two custom roles, combining them SHALL produce the union of permissions.
        """
        role1 = Role(name="custom_role_1", permissions=permissions1)
        role2 = Role(name="custom_role_2", permissions=permissions2)

        service = RBACService(roles={
            role1.name: role1,
            role2.name: role2,
        })

        user = RBACUser(id=user_id, roles=[role1.name, role2.name])
        combined = service.get_user_permissions(user)

        expected = permissions1 | permissions2
        assert combined == expected, "Combined permissions should be union"

    @settings(max_examples=50, deadline=None)
    @given(user_id=user_id_strategy)
    def test_admin_role_has_all_permissions(self, user_id: str) -> None:
        """
        **Feature: api-base-improvements, Property 8: Multiple roles combine permissions**
        **Validates: Requirements 2.3**

        Admin role SHALL have all permissions.
        """
        user = RBACUser(id=user_id, roles=["admin"])
        service = RBACService()

        permissions = service.get_user_permissions(user)

        # Admin should have all permissions
        for perm in Permission:
            assert perm in permissions, f"Admin should have {perm}"

    @settings(max_examples=50, deadline=None)
    @given(user_id=user_id_strategy)
    def test_moderator_permissions_are_correct(self, user_id: str) -> None:
        """
        **Feature: api-base-improvements, Property 8: Multiple roles combine permissions**
        **Validates: Requirements 2.3**

        Moderator role SHALL have READ, WRITE, DELETE, and VIEW_AUDIT permissions.
        """
        user = RBACUser(id=user_id, roles=["moderator"])
        service = RBACService()

        permissions = service.get_user_permissions(user)

        assert Permission.READ in permissions
        assert Permission.WRITE in permissions
        assert Permission.DELETE in permissions
        assert Permission.VIEW_AUDIT in permissions
        assert Permission.ADMIN not in permissions

    @settings(max_examples=50, deadline=None)
    @given(user_id=user_id_strategy)
    def test_scopes_add_to_permissions(self, user_id: str) -> None:
        """
        **Feature: api-base-improvements, Property 8: Multiple roles combine permissions**
        **Validates: Requirements 2.3**

        OAuth2 scopes SHALL be added to role permissions.
        """
        user = RBACUser(
            id=user_id,
            roles=["viewer"],
            scopes=["write", "delete"],
        )
        service = RBACService()

        permissions = service.get_user_permissions(user)

        # Should have viewer permissions plus scopes
        assert Permission.READ in permissions  # from viewer role
        assert Permission.WRITE in permissions  # from scope
        assert Permission.DELETE in permissions  # from scope


class TestRoleDataclass:
    """Property tests for Role dataclass."""

    @settings(max_examples=100, deadline=None)
    @given(
        role_name=role_name_strategy,
        permissions=permission_set_strategy,
    )
    def test_role_serialization_round_trip(
        self, role_name: str, permissions: frozenset[Permission]
    ) -> None:
        """
        **Feature: api-base-improvements, Property 8: Multiple roles combine permissions**
        **Validates: Requirements 2.3**

        Role serialization and deserialization SHALL preserve all data.
        """
        original = Role(
            name=role_name,
            permissions=permissions,
            description="Test role",
        )

        serialized = original.to_dict()
        deserialized = Role.from_dict(serialized)

        assert deserialized.name == original.name
        assert deserialized.permissions == original.permissions
        assert deserialized.description == original.description

    @settings(max_examples=50, deadline=None)
    @given(permissions=permission_set_strategy, permission=permission_strategy)
    def test_has_permission_method(
        self, permissions: frozenset[Permission], permission: Permission
    ) -> None:
        """
        **Feature: api-base-improvements, Property 8: Multiple roles combine permissions**
        **Validates: Requirements 2.3**

        Role.has_permission SHALL return True iff permission is in role.
        """
        role = Role(name="test", permissions=permissions)
        expected = permission in permissions
        assert role.has_permission(permission) == expected
