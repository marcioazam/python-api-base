"""Unit tests for examples RBAC permissions.

**Feature: infrastructure-modules-integration-analysis**
**Validates: Requirements 4.3**
"""

import pytest
from dataclasses import dataclass

from interface.v1.examples.permissions import (
    ExampleResource,
    ExampleAction,
    ITEM_READ,
    ITEM_CREATE,
    ITEM_DELETE,
    PEDIDO_READ,
    PEDIDO_CONFIRM,
    setup_example_roles,
)
from infrastructure.rbac import Permission, RoleRegistry, RBAC


@dataclass
class TestUser:
    """Test user for RBAC tests."""

    id: str
    roles: list[str]


class TestExamplePermissions:
    """Tests for example permissions.
    
    **Feature: infrastructure-modules-integration-analysis**
    **Validates: Requirements 4.3**
    """

    def test_item_permissions_defined(self) -> None:
        """Test item permissions are defined correctly."""
        assert ITEM_READ.resource == ExampleResource.ITEM
        assert ITEM_READ.action == ExampleAction.READ

        assert ITEM_CREATE.resource == ExampleResource.ITEM
        assert ITEM_CREATE.action == ExampleAction.CREATE

        assert ITEM_DELETE.resource == ExampleResource.ITEM
        assert ITEM_DELETE.action == ExampleAction.DELETE

    def test_pedido_permissions_defined(self) -> None:
        """Test pedido permissions are defined correctly."""
        assert PEDIDO_READ.resource == ExampleResource.PEDIDO
        assert PEDIDO_READ.action == ExampleAction.READ

        assert PEDIDO_CONFIRM.resource == ExampleResource.PEDIDO
        assert PEDIDO_CONFIRM.action == ExampleAction.CONFIRM


class TestExampleRoles:
    """Tests for example roles.
    
    **Feature: infrastructure-modules-integration-analysis**
    **Validates: Requirements 4.3**
    """

    @pytest.fixture
    def registry(self) -> RoleRegistry:
        """Create role registry with example roles."""
        registry = RoleRegistry[ExampleResource, ExampleAction]()
        setup_example_roles(registry)
        return registry

    @pytest.fixture
    def rbac(self, registry: RoleRegistry) -> RBAC:
        """Create RBAC checker."""
        return RBAC[TestUser, ExampleResource, ExampleAction](registry)

    def test_viewer_can_read_items(self, rbac: RBAC) -> None:
        """Test viewer role can read items.
        
        **Validates: Requirements 4.3**
        """
        user = TestUser(id="user-1", roles=["example_viewer"])
        assert rbac.has_permission(user, ITEM_READ)

    def test_viewer_cannot_create_items(self, rbac: RBAC) -> None:
        """Test viewer role cannot create items.
        
        **Validates: Requirements 4.3**
        """
        user = TestUser(id="user-1", roles=["example_viewer"])
        assert not rbac.has_permission(user, ITEM_CREATE)

    def test_viewer_cannot_delete_items(self, rbac: RBAC) -> None:
        """Test viewer role cannot delete items.
        
        **Validates: Requirements 4.3**
        """
        user = TestUser(id="user-1", roles=["example_viewer"])
        assert not rbac.has_permission(user, ITEM_DELETE)

    def test_editor_can_create_items(self, rbac: RBAC) -> None:
        """Test editor role can create items.
        
        **Validates: Requirements 4.3**
        """
        user = TestUser(id="user-1", roles=["example_editor"])
        assert rbac.has_permission(user, ITEM_CREATE)

    def test_editor_inherits_viewer(self, rbac: RBAC) -> None:
        """Test editor role inherits viewer permissions.
        
        **Validates: Requirements 4.3**
        """
        user = TestUser(id="user-1", roles=["example_editor"])
        assert rbac.has_permission(user, ITEM_READ)

    def test_editor_cannot_delete_items(self, rbac: RBAC) -> None:
        """Test editor role cannot delete items.
        
        **Validates: Requirements 4.3**
        """
        user = TestUser(id="user-1", roles=["example_editor"])
        assert not rbac.has_permission(user, ITEM_DELETE)

    def test_admin_can_delete_items(self, rbac: RBAC) -> None:
        """Test admin role can delete items.
        
        **Validates: Requirements 4.3**
        """
        user = TestUser(id="user-1", roles=["example_admin"])
        assert rbac.has_permission(user, ITEM_DELETE)

    def test_admin_inherits_all(self, rbac: RBAC) -> None:
        """Test admin role inherits all permissions.
        
        **Validates: Requirements 4.3**
        """
        user = TestUser(id="user-1", roles=["example_admin"])
        assert rbac.has_permission(user, ITEM_READ)
        assert rbac.has_permission(user, ITEM_CREATE)
        assert rbac.has_permission(user, ITEM_DELETE)
        assert rbac.has_permission(user, PEDIDO_READ)
        assert rbac.has_permission(user, PEDIDO_CONFIRM)
