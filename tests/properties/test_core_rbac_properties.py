"""Property-based tests for RBAC module.

**Feature: core-code-review**
**Validates: Requirements 8.1, 8.3, 8.5**
"""

import string
from typing import Any

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from my_app.core.auth.rbac import (
    Permission,
    Role,
    RBACService,
    RBACUser,
    require_permission,
    ROLE_ADMIN,
    ROLE_USER,
    ROLE_VIEWER,
)
from my_app.core.exceptions import AuthorizationError


class TestRBACPermissionInheritance:
    """Property tests for RBAC permission inheritance.
    
    **Feature: core-code-review, Property 15: RBAC Permission Inheritance**
    **Validates: Requirements 8.1**
    """

    @given(
        role_names=st.lists(
            st.sampled_from(["admin", "user", "viewer", "moderator"]),
            min_size=1,
            max_size=4,
            unique=True,
        )
    )
    @settings(max_examples=50)
    def test_user_gets_union_of_role_permissions(self, role_names: list[str]):
        """For any user with roles, permissions SHALL be union of all role permissions."""
        service = RBACService()
        user = RBACUser(id="user123", roles=role_names)
        
        # Get user permissions
        user_permissions = service.get_user_permissions(user)
        
        # Calculate expected permissions (union of all roles)
        expected_permissions: set[Permission] = set()
        for role_name in role_names:
            role = service.get_role(role_name)
            if role:
                expected_permissions.update(role.permissions)
        
        assert user_permissions == expected_permissions

    def test_admin_has_all_permissions(self):
        """Admin role SHALL have all permissions."""
        service = RBACService()
        user = RBACUser(id="admin123", roles=["admin"])
        
        permissions = service.get_user_permissions(user)
        
        # Admin should have all Permission enum values
        assert permissions == set(Permission)


class TestRBACAnyAllSemantics:
    """Property tests for RBAC ANY/ALL semantics.
    
    **Feature: core-code-review, Property 16: RBAC ANY/ALL Semantics**
    **Validates: Requirements 8.3**
    """

    @given(
        user_permissions=st.lists(
            st.sampled_from(list(Permission)),
            min_size=1,
            max_size=5,
            unique=True,
        ),
        required_permissions=st.lists(
            st.sampled_from(list(Permission)),
            min_size=1,
            max_size=3,
            unique=True,
        ),
    )
    @settings(max_examples=100)
    def test_check_any_permission_semantics(
        self, user_permissions: list[Permission], required_permissions: list[Permission]
    ):
        """check_any_permission() SHALL return True if at least one permission present."""
        # Create custom role with specific permissions
        custom_role = Role(
            name="custom",
            permissions=frozenset(user_permissions),
        )
        service = RBACService(roles={"custom": custom_role})
        user = RBACUser(id="user123", roles=["custom"])
        
        result = service.check_any_permission(user, required_permissions)
        
        # Should be True if there's any intersection
        has_any = bool(set(user_permissions) & set(required_permissions))
        assert result == has_any

    @given(
        user_permissions=st.lists(
            st.sampled_from(list(Permission)),
            min_size=1,
            max_size=5,
            unique=True,
        ),
        required_permissions=st.lists(
            st.sampled_from(list(Permission)),
            min_size=1,
            max_size=3,
            unique=True,
        ),
    )
    @settings(max_examples=100)
    def test_check_all_permissions_semantics(
        self, user_permissions: list[Permission], required_permissions: list[Permission]
    ):
        """check_all_permissions() SHALL return True only if all permissions present."""
        custom_role = Role(
            name="custom",
            permissions=frozenset(user_permissions),
        )
        service = RBACService(roles={"custom": custom_role})
        user = RBACUser(id="user123", roles=["custom"])
        
        result = service.check_all_permissions(user, required_permissions)
        
        # Should be True only if all required are in user permissions
        has_all = set(required_permissions).issubset(set(user_permissions))
        assert result == has_all


class TestRBACDecoratorCompatibility:
    """Property tests for RBAC decorator compatibility.
    
    **Feature: core-code-review, Property 17: RBAC Decorator Compatibility**
    **Validates: Requirements 8.5**
    """

    def test_decorator_works_with_sync_function(self):
        """Decorator SHALL work with sync functions."""
        @require_permission(Permission.READ)
        def sync_function(user: RBACUser) -> str:
            return "success"
        
        user = RBACUser(id="user123", roles=["user"])
        result = sync_function(user=user)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_works_with_async_function(self):
        """Decorator SHALL work with async functions."""
        @require_permission(Permission.READ)
        async def async_function(user: RBACUser) -> str:
            return "success"
        
        user = RBACUser(id="user123", roles=["user"])
        result = await async_function(user=user)
        assert result == "success"

    def test_decorator_raises_on_missing_permission(self):
        """Decorator SHALL raise AuthorizationError when permission missing."""
        @require_permission(Permission.ADMIN)
        def admin_function(user: RBACUser) -> str:
            return "success"
        
        user = RBACUser(id="user123", roles=["viewer"])  # Viewer has only READ
        
        with pytest.raises(AuthorizationError):
            admin_function(user=user)

    def test_decorator_raises_on_missing_user(self):
        """Decorator SHALL raise AuthorizationError when user not provided."""
        @require_permission(Permission.READ)
        def protected_function() -> str:
            return "success"
        
        with pytest.raises(AuthorizationError):
            protected_function()


class TestRoleOperations:
    """Tests for Role operations."""

    @given(
        name=st.text(min_size=1, max_size=30, alphabet=string.ascii_lowercase),
        permissions=st.lists(st.sampled_from(list(Permission)), min_size=0, max_size=5, unique=True),
    )
    @settings(max_examples=50)
    def test_role_to_dict_round_trip(self, name: str, permissions: list[Permission]):
        """Role.to_dict/from_dict SHALL round-trip correctly."""
        assume(len(name) > 0)
        
        role = Role(
            name=name,
            permissions=frozenset(permissions),
            description="Test role",
        )
        
        data = role.to_dict()
        restored = Role.from_dict(data)
        
        assert restored.name == role.name
        assert restored.permissions == role.permissions
        assert restored.description == role.description

    def test_role_has_permission(self):
        """Role.has_permission() SHALL correctly check permissions."""
        role = Role(
            name="test",
            permissions=frozenset([Permission.READ, Permission.WRITE]),
        )
        
        assert role.has_permission(Permission.READ)
        assert role.has_permission(Permission.WRITE)
        assert not role.has_permission(Permission.DELETE)


class TestRBACServiceOperations:
    """Tests for RBACService operations."""

    def test_add_role(self):
        """add_role() SHALL add or update roles."""
        service = RBACService()
        
        new_role = Role(
            name="custom",
            permissions=frozenset([Permission.READ]),
        )
        service.add_role(new_role)
        
        retrieved = service.get_role("custom")
        assert retrieved is not None
        assert retrieved.permissions == frozenset([Permission.READ])

    def test_scope_based_permissions(self):
        """Scopes SHALL be converted to permissions."""
        service = RBACService()
        user = RBACUser(
            id="user123",
            roles=[],
            scopes=["read", "write"],
        )
        
        permissions = service.get_user_permissions(user)
        
        assert Permission.READ in permissions
        assert Permission.WRITE in permissions
