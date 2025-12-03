"""Property-based tests for RBAC Permission Composition.

**Feature: architecture-restructuring-2025, Property 13: RBAC Permission Composition**
**Validates: Requirements 9.3**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

try:
    from infrastructure.security.rbac import (
        RBACService,
        RBACUser,
        Role,
        Permission,
        ROLE_ADMIN,
        ROLE_USER,
        ROLE_VIEWER,
        ROLE_MODERATOR,
    )
except ImportError:
    pytest.skip("my_app modules not available", allow_module_level=True)


# Strategy for permissions
permission_strategy = st.sampled_from(list(Permission))
permissions_set_strategy = st.frozensets(permission_strategy, min_size=0, max_size=len(Permission))

# Strategy for role names
role_name_strategy = st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz_")

# Strategy for user IDs
user_id_strategy = st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_")


class TestRBACPermissionComposition:
    """Property tests for RBAC permission composition."""

    @settings(max_examples=50)
    @given(
        role_name=role_name_strategy,
        permissions=permissions_set_strategy,
        check_permission=permission_strategy,
    )
    def test_role_has_permission_iff_in_set(
        self, role_name: str, permissions: frozenset[Permission], check_permission: Permission
    ) -> None:
        """
        **Feature: architecture-restructuring-2025, Property 13: RBAC Permission Composition**
        
        For any role with a set of permissions, checking if the role has a specific
        permission SHALL return True if and only if that permission is in the set.
        **Validates: Requirements 9.3**
        """
        role = Role(name=role_name, permissions=permissions)
        
        expected = check_permission in permissions
        actual = role.has_permission(check_permission)
        
        assert actual == expected

    @settings(max_examples=50)
    @given(
        user_id=user_id_strategy,
        role1_perms=permissions_set_strategy,
        role2_perms=permissions_set_strategy,
    )
    def test_user_permissions_union_of_roles(
        self, user_id: str, role1_perms: frozenset[Permission], role2_perms: frozenset[Permission]
    ) -> None:
        """
        For any user with multiple roles, their permissions SHALL be the union
        of all role permissions.
        **Validates: Requirements 9.3**
        """
        role1 = Role(name="role1", permissions=role1_perms)
        role2 = Role(name="role2", permissions=role2_perms)
        
        service = RBACService(roles={"role1": role1, "role2": role2})
        user = RBACUser(id=user_id, roles=["role1", "role2"])
        
        user_permissions = service.get_user_permissions(user)
        expected_permissions = role1_perms | role2_perms
        
        assert user_permissions == expected_permissions

    @settings(max_examples=50)
    @given(
        user_id=user_id_strategy,
        permissions=permissions_set_strategy,
        check_permission=permission_strategy,
    )
    def test_check_permission_matches_get_permissions(
        self, user_id: str, permissions: frozenset[Permission], check_permission: Permission
    ) -> None:
        """
        For any user, check_permission SHALL return True iff the permission
        is in get_user_permissions result.
        **Validates: Requirements 9.3**
        """
        role = Role(name="test_role", permissions=permissions)
        service = RBACService(roles={"test_role": role})
        user = RBACUser(id=user_id, roles=["test_role"])
        
        user_perms = service.get_user_permissions(user)
        expected = check_permission in user_perms
        actual = service.check_permission(user, check_permission)
        
        assert actual == expected

    @settings(max_examples=30)
    @given(
        user_id=user_id_strategy,
        permissions=permissions_set_strategy,
        required_perms=st.lists(permission_strategy, min_size=1, max_size=3),
    )
    def test_check_any_permission(
        self, user_id: str, permissions: frozenset[Permission], required_perms: list[Permission]
    ) -> None:
        """
        For any user, check_any_permission SHALL return True iff at least one
        required permission is in user's permissions.
        **Validates: Requirements 9.3**
        """
        role = Role(name="test_role", permissions=permissions)
        service = RBACService(roles={"test_role": role})
        user = RBACUser(id=user_id, roles=["test_role"])
        
        expected = bool(permissions & set(required_perms))
        actual = service.check_any_permission(user, required_perms)
        
        assert actual == expected

    @settings(max_examples=30)
    @given(
        user_id=user_id_strategy,
        permissions=permissions_set_strategy,
        required_perms=st.lists(permission_strategy, min_size=1, max_size=3),
    )
    def test_check_all_permissions(
        self, user_id: str, permissions: frozenset[Permission], required_perms: list[Permission]
    ) -> None:
        """
        For any user, check_all_permissions SHALL return True iff all
        required permissions are in user's permissions.
        **Validates: Requirements 9.3**
        """
        role = Role(name="test_role", permissions=permissions)
        service = RBACService(roles={"test_role": role})
        user = RBACUser(id=user_id, roles=["test_role"])
        
        expected = set(required_perms).issubset(permissions)
        actual = service.check_all_permissions(user, required_perms)
        
        assert actual == expected

    def test_admin_role_has_all_permissions(self) -> None:
        """
        The admin role SHALL have all defined permissions.
        **Validates: Requirements 9.3**
        """
        for permission in Permission:
            assert ROLE_ADMIN.has_permission(permission)

    def test_predefined_roles_hierarchy(self) -> None:
        """
        Predefined roles SHALL follow expected permission hierarchy.
        **Validates: Requirements 9.3**
        """
        # Admin has all permissions
        assert len(ROLE_ADMIN.permissions) == len(Permission)
        
        # User has read and write
        assert ROLE_USER.has_permission(Permission.READ)
        assert ROLE_USER.has_permission(Permission.WRITE)
        assert not ROLE_USER.has_permission(Permission.ADMIN)
        
        # Viewer has only read
        assert ROLE_VIEWER.has_permission(Permission.READ)
        assert not ROLE_VIEWER.has_permission(Permission.WRITE)
        
        # Moderator has specific permissions
        assert ROLE_MODERATOR.has_permission(Permission.DELETE)
        assert ROLE_MODERATOR.has_permission(Permission.VIEW_AUDIT)
