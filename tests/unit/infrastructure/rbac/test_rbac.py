"""Unit tests for generic RBAC system.

**Feature: enterprise-generics-2025**
**Requirement: R14 - Generic RBAC System**
"""

import pytest
from enum import Enum
from dataclasses import dataclass

from infrastructure.rbac.permission import (
    Permission,
    PermissionSet,
    StandardResource,
    StandardAction,
    create_crud_permissions,
)
from infrastructure.rbac.role import Role, RoleRegistry, create_standard_roles
from infrastructure.rbac.checker import RBAC
from infrastructure.rbac.audit import AuditEvent, AuditLogger, InMemoryAuditSink


# =============================================================================
# Test Enums
# =============================================================================


class TestResource(str, Enum):
    """Test resource types."""

    DOCUMENT = "document"
    REPORT = "report"
    USER = "user"


class TestAction(str, Enum):
    """Test action types."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"


# =============================================================================
# Test User
# =============================================================================


@dataclass
class TestUser:
    """Test user with roles."""

    id: str
    roles: list[str]


# =============================================================================
# Tests
# =============================================================================


class TestPermission:
    """Tests for Permission."""

    def test_permission_creation(self) -> None:
        """Test permission can be created."""
        perm = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.READ,
        )

        assert perm.resource == TestResource.DOCUMENT
        assert perm.action == TestAction.READ

    def test_permission_str(self) -> None:
        """Test permission string representation."""
        perm = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.READ,
        )

        assert str(perm) == "document:read"

    def test_permission_matches(self) -> None:
        """Test permission matching."""
        perm = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.READ,
        )

        assert perm.matches(TestResource.DOCUMENT, TestAction.READ)
        assert not perm.matches(TestResource.REPORT, TestAction.READ)

    def test_permission_with_condition(self) -> None:
        """Test adding condition to permission."""
        perm = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.UPDATE,
        )

        perm_own = perm.with_condition("own")

        assert perm_own.conditions == frozenset({"own"})

    def test_permission_hashable(self) -> None:
        """Test permission is hashable for set operations."""
        perm1 = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.READ,
        )
        perm2 = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.READ,
        )

        perms = {perm1, perm2}
        assert len(perms) == 1


class TestPermissionSet:
    """Tests for PermissionSet."""

    def test_add_permission(self) -> None:
        """Test adding permission to set."""
        perm_set = PermissionSet[TestResource, TestAction]()
        perm = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.READ,
        )

        perm_set.add(perm)

        assert perm in perm_set
        assert len(perm_set) == 1

    def test_has_permission(self) -> None:
        """Test checking permission in set."""
        perm_set = PermissionSet[TestResource, TestAction]()
        perm = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.READ,
        )
        perm_set.add(perm)

        assert perm_set.has(TestResource.DOCUMENT, TestAction.READ)
        assert not perm_set.has(TestResource.REPORT, TestAction.READ)

    def test_union(self) -> None:
        """Test union of permission sets."""
        set1 = PermissionSet[TestResource, TestAction]({
            Permission(TestResource.DOCUMENT, TestAction.READ),
        })
        set2 = PermissionSet[TestResource, TestAction]({
            Permission(TestResource.REPORT, TestAction.READ),
        })

        combined = set1 | set2

        assert len(combined) == 2


class TestRole:
    """Tests for Role."""

    def test_role_creation(self) -> None:
        """Test role can be created."""
        role = Role[Permission[TestResource, TestAction]](
            name="admin",
            description="Administrator",
            permissions={
                Permission(TestResource.DOCUMENT, TestAction.DELETE),
            },
        )

        assert role.name == "admin"
        assert len(role.permissions) == 1

    def test_has_permission(self) -> None:
        """Test role permission check."""
        perm = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.READ,
        )
        role = Role[Permission[TestResource, TestAction]](
            name="viewer",
            permissions={perm},
        )

        assert role.has_permission(perm)

    def test_role_inheritance(self) -> None:
        """Test role inherits from parent."""
        viewer_perm = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.READ,
        )
        editor_perm = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.UPDATE,
        )

        viewer = Role[Permission[TestResource, TestAction]](
            name="viewer",
            permissions={viewer_perm},
        )
        editor = Role[Permission[TestResource, TestAction]](
            name="editor",
            permissions={editor_perm},
        ).inherits_from(viewer)

        # Editor has own permission
        assert editor.has_permission(editor_perm)
        # Editor inherits viewer permission
        assert editor.has_permission(viewer_perm)

    def test_get_all_permissions(self) -> None:
        """Test getting all permissions including inherited."""
        perm1 = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.READ,
        )
        perm2 = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.UPDATE,
        )

        parent = Role[Permission[TestResource, TestAction]](
            name="parent",
            permissions={perm1},
        )
        child = Role[Permission[TestResource, TestAction]](
            name="child",
            permissions={perm2},
            parent=parent,
        )

        all_perms = child.get_all_permissions()

        assert perm1 in all_perms
        assert perm2 in all_perms


class TestRoleRegistry:
    """Tests for RoleRegistry."""

    @pytest.fixture
    def registry(self) -> RoleRegistry[TestResource, TestAction]:
        """Create test registry."""
        return RoleRegistry[TestResource, TestAction]()

    def test_register_role(
        self,
        registry: RoleRegistry[TestResource, TestAction],
    ) -> None:
        """Test registering role."""
        role = Role[Permission[TestResource, TestAction]](
            name="viewer",
            permissions=set(),
        )

        registry.register(role)

        assert registry.get("viewer") == role

    def test_create_role(
        self,
        registry: RoleRegistry[TestResource, TestAction],
    ) -> None:
        """Test creating role through registry."""
        role = registry.create_role(
            name="editor",
            permissions={
                Permission(TestResource.DOCUMENT, TestAction.UPDATE),
            },
            description="Editor role",
        )

        assert registry.get("editor") == role

    def test_create_role_with_parent(
        self,
        registry: RoleRegistry[TestResource, TestAction],
    ) -> None:
        """Test creating role with parent."""
        registry.create_role(
            name="viewer",
            permissions={Permission(TestResource.DOCUMENT, TestAction.READ)},
        )
        editor = registry.create_role(
            name="editor",
            permissions={Permission(TestResource.DOCUMENT, TestAction.UPDATE)},
            parent="viewer",
        )

        assert editor.parent is not None
        assert editor.parent.name == "viewer"


class TestRBAC:
    """Tests for RBAC checker."""

    @pytest.fixture
    def registry(self) -> RoleRegistry[TestResource, TestAction]:
        """Create test registry with roles."""
        registry = RoleRegistry[TestResource, TestAction]()

        registry.create_role(
            name="viewer",
            permissions={
                Permission(TestResource.DOCUMENT, TestAction.READ),
                Permission(TestResource.DOCUMENT, TestAction.LIST),
            },
        )
        registry.create_role(
            name="editor",
            permissions={
                Permission(TestResource.DOCUMENT, TestAction.CREATE),
                Permission(TestResource.DOCUMENT, TestAction.UPDATE),
            },
            parent="viewer",
        )
        registry.create_role(
            name="admin",
            permissions={
                Permission(TestResource.DOCUMENT, TestAction.DELETE),
            },
            parent="editor",
        )

        return registry

    @pytest.fixture
    def rbac(
        self,
        registry: RoleRegistry[TestResource, TestAction],
    ) -> RBAC[TestUser, TestResource, TestAction]:
        """Create RBAC checker."""
        return RBAC[TestUser, TestResource, TestAction](registry)

    def test_viewer_has_read(
        self,
        rbac: RBAC[TestUser, TestResource, TestAction],
    ) -> None:
        """Test viewer can read."""
        user = TestUser(id="1", roles=["viewer"])
        perm = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.READ,
        )

        assert rbac.has_permission(user, perm)

    def test_viewer_cannot_delete(
        self,
        rbac: RBAC[TestUser, TestResource, TestAction],
    ) -> None:
        """Test viewer cannot delete."""
        user = TestUser(id="1", roles=["viewer"])
        perm = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.DELETE,
        )

        assert not rbac.has_permission(user, perm)

    def test_admin_can_delete(
        self,
        rbac: RBAC[TestUser, TestResource, TestAction],
    ) -> None:
        """Test admin can delete."""
        user = TestUser(id="1", roles=["admin"])
        perm = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.DELETE,
        )

        assert rbac.has_permission(user, perm)

    def test_admin_inherits_viewer(
        self,
        rbac: RBAC[TestUser, TestResource, TestAction],
    ) -> None:
        """Test admin inherits viewer permissions."""
        user = TestUser(id="1", roles=["admin"])
        read_perm = Permission[TestResource, TestAction](
            resource=TestResource.DOCUMENT,
            action=TestAction.READ,
        )

        assert rbac.has_permission(user, read_perm)

    def test_get_user_permissions(
        self,
        rbac: RBAC[TestUser, TestResource, TestAction],
    ) -> None:
        """Test getting all user permissions."""
        user = TestUser(id="1", roles=["editor"])

        perms = rbac.get_user_permissions(user)

        # Editor has own + inherited from viewer
        assert len(perms) >= 4  # read, list, create, update


class TestAuditEvent:
    """Tests for AuditEvent."""

    def test_create_event(self) -> None:
        """Test creating audit event."""
        event = AuditEvent.create(
            user_id="user_123",
            user_roles=["admin"],
            resource=TestResource.DOCUMENT,
            action=TestAction.DELETE,
            resource_id="doc_456",
            granted=True,
        )

        assert event.user_id == "user_123"
        assert event.granted
        assert event.resource == TestResource.DOCUMENT

    def test_to_dict(self) -> None:
        """Test event serialization."""
        event = AuditEvent.create(
            user_id="user_123",
            user_roles=["admin"],
            resource=TestResource.DOCUMENT,
            action=TestAction.DELETE,
            resource_id="doc_456",
            granted=True,
        )

        data = event.to_dict()

        assert data["user_id"] == "user_123"
        assert data["resource"] == "document"
        assert data["action"] == "delete"


class TestAuditLogger:
    """Tests for AuditLogger."""

    @pytest.mark.asyncio
    async def test_log_to_sink(self) -> None:
        """Test logging to in-memory sink."""
        sink = InMemoryAuditSink()
        logger = AuditLogger[TestUser, TestResource, TestAction](sink=sink)

        event = AuditEvent.create(
            user_id="user_123",
            user_roles=["admin"],
            resource=TestResource.DOCUMENT,
            action=TestAction.DELETE,
            resource_id="doc_456",
            granted=True,
        )

        await logger.log(event)

        assert len(sink.events) == 1
        assert sink.events[0]["user_id"] == "user_123"

    @pytest.mark.asyncio
    async def test_log_access_convenience(self) -> None:
        """Test log_access convenience method."""
        sink = InMemoryAuditSink()
        logger = AuditLogger[TestUser, TestResource, TestAction](sink=sink)

        await logger.log_access(
            user_id="user_123",
            user_roles=["viewer"],
            resource=TestResource.REPORT,
            action=TestAction.READ,
            resource_id="report_789",
            granted=True,
        )

        assert len(sink.events) == 1
        assert sink.events[0]["resource"] == "report"


class TestCRUDPermissions:
    """Tests for CRUD permission factory."""

    def test_create_crud_permissions(self) -> None:
        """Test creating CRUD permissions for resource."""
        perms = create_crud_permissions(TestResource.DOCUMENT)

        assert len(perms) == 5
        assert perms.has(TestResource.DOCUMENT, StandardAction.CREATE)
        assert perms.has(TestResource.DOCUMENT, StandardAction.READ)
        assert perms.has(TestResource.DOCUMENT, StandardAction.UPDATE)
        assert perms.has(TestResource.DOCUMENT, StandardAction.DELETE)
        assert perms.has(TestResource.DOCUMENT, StandardAction.LIST)
