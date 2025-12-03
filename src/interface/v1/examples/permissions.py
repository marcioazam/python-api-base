"""RBAC permissions for examples.

**Feature: infrastructure-modules-integration-analysis**
**Validates: Requirements 4.3**

Defines permissions for ItemExample and PedidoExample resources.
"""

from enum import Enum

from infrastructure.rbac import Permission, RoleRegistry


class ExampleResource(str, Enum):
    """Resources for examples."""

    ITEM = "item"
    PEDIDO = "pedido"


class ExampleAction(str, Enum):
    """Actions for examples."""

    READ = "read"
    LIST = "list"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    CONFIRM = "confirm"
    CANCEL = "cancel"


# Pre-defined permissions
ITEM_READ = Permission(ExampleResource.ITEM, ExampleAction.READ)
ITEM_LIST = Permission(ExampleResource.ITEM, ExampleAction.LIST)
ITEM_CREATE = Permission(ExampleResource.ITEM, ExampleAction.CREATE)
ITEM_UPDATE = Permission(ExampleResource.ITEM, ExampleAction.UPDATE)
ITEM_DELETE = Permission(ExampleResource.ITEM, ExampleAction.DELETE)

PEDIDO_READ = Permission(ExampleResource.PEDIDO, ExampleAction.READ)
PEDIDO_LIST = Permission(ExampleResource.PEDIDO, ExampleAction.LIST)
PEDIDO_CREATE = Permission(ExampleResource.PEDIDO, ExampleAction.CREATE)
PEDIDO_CONFIRM = Permission(ExampleResource.PEDIDO, ExampleAction.CONFIRM)
PEDIDO_CANCEL = Permission(ExampleResource.PEDIDO, ExampleAction.CANCEL)


def setup_example_roles(registry: RoleRegistry) -> None:
    """Setup roles for examples.

    **Feature: infrastructure-modules-integration-analysis**
    **Validates: Requirements 4.3**

    Creates:
    - example_viewer: Read-only access to items and pedidos
    - example_editor: Create and update items and pedidos
    - example_admin: Full access including delete
    """
    # Viewer role - read only
    registry.create_role(
        name="example_viewer",
        permissions={
            ITEM_READ,
            ITEM_LIST,
            PEDIDO_READ,
            PEDIDO_LIST,
        },
        description="Read-only access to examples",
    )

    # Editor role - create and update
    registry.create_role(
        name="example_editor",
        permissions={
            ITEM_CREATE,
            ITEM_UPDATE,
            PEDIDO_CREATE,
            PEDIDO_CONFIRM,
        },
        description="Create and update examples",
        parent="example_viewer",
    )

    # Admin role - full access
    registry.create_role(
        name="example_admin",
        permissions={
            ITEM_DELETE,
            PEDIDO_CANCEL,
        },
        description="Full access to examples",
        parent="example_editor",
    )
