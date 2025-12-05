"""GraphQL Mutation root for Examples.

**Feature: interface-modules-workflow-analysis**
**Validates: Requirements 3.3**
**Improvement: P2-1 - Use CQRS pattern**
"""

from decimal import Decimal

import strawberry
from strawberry.types import Info

from application.common.cqrs import CommandBus
from application.examples.item.commands import (
    CreateItemCommand,
    DeleteItemCommand,
    UpdateItemCommand,
)
from application.examples.pedido.commands import (
    ConfirmPedidoCommand,
    CreatePedidoCommand,
)
from core.base.patterns.result import Err, Ok
from application.mappers.graphql import (
    map_item_dto_to_type,
    map_pedido_dto_to_type,
)
from interface.graphql.types import (
    ItemCreateInput,
    ItemMutationResult,
    ItemUpdateInput,
    MutationResult,
    PedidoCreateInput,
    PedidoMutationResult,
)


def get_command_bus(info: Info) -> CommandBus | None:
    """Get CommandBus from context."""
    return info.context.get("command_bus")


@strawberry.type
class Mutation:
    """GraphQL Mutation root for Examples."""

    @strawberry.mutation
    async def create_item(
        self, info: Info, input: ItemCreateInput
    ) -> ItemMutationResult:
        """Create a new item."""
        command_bus = get_command_bus(info)
        if command_bus is None:
            return ItemMutationResult(success=False, error="CommandBus not available")

        command = CreateItemCommand(
            name=input.name,
            sku=f"AUTO-{input.name[:3].upper()}-001",
            price_amount=Decimal(str(input.price)),
            price_currency="BRL",
            description=input.description or "",
            quantity=input.quantity,
            category=input.category,
        )

        result = await command_bus.dispatch(command)

        match result:
            case Ok(item_dto):
                return ItemMutationResult(
                    success=True,
                    item=map_item_dto_to_type(item_dto),
                )
            case Err(error):
                return ItemMutationResult(success=False, error=str(error))

    @strawberry.mutation
    async def update_item(
        self, info: Info, id: str, input: ItemUpdateInput
    ) -> ItemMutationResult:
        """Update an existing item."""
        command_bus = get_command_bus(info)
        if command_bus is None:
            return ItemMutationResult(success=False, error="CommandBus not available")

        command = UpdateItemCommand(
            item_id=id,
            name=input.name,
            description=input.description,
            price_amount=Decimal(str(input.price)) if input.price is not None else None,
            quantity=input.quantity,
            category=input.category,
        )

        result = await command_bus.dispatch(command)

        match result:
            case Ok(item_dto):
                return ItemMutationResult(
                    success=True,
                    item=map_item_dto_to_type(item_dto),
                )
            case Err(error):
                return ItemMutationResult(success=False, error=str(error))

    @strawberry.mutation
    async def delete_item(self, info: Info, id: str) -> MutationResult:
        """Delete an item."""
        command_bus = get_command_bus(info)
        if command_bus is None:
            return MutationResult(success=False, message="CommandBus not available")

        command = DeleteItemCommand(item_id=id)
        result = await command_bus.dispatch(command)

        match result:
            case Ok(_):
                return MutationResult(success=True, message="Item deleted")
            case Err(error):
                return MutationResult(success=False, message=str(error))

    @strawberry.mutation
    async def create_pedido(
        self, info: Info, input: PedidoCreateInput
    ) -> PedidoMutationResult:
        """Create a new pedido."""
        command_bus = get_command_bus(info)
        if command_bus is None:
            return PedidoMutationResult(success=False, error="CommandBus not available")

        command = CreatePedidoCommand(
            customer_id=input.customer_id,
            customer_name="Default Customer",
            customer_email="customer@example.com",
        )

        result = await command_bus.dispatch(command)

        match result:
            case Ok(pedido_dto):
                return PedidoMutationResult(
                    success=True,
                    pedido=map_pedido_dto_to_type(pedido_dto),
                )
            case Err(error):
                return PedidoMutationResult(success=False, error=str(error))

    @strawberry.mutation
    async def confirm_pedido(self, info: Info, id: str) -> PedidoMutationResult:
        """Confirm a pedido."""
        command_bus = get_command_bus(info)
        if command_bus is None:
            return PedidoMutationResult(success=False, error="CommandBus not available")

        command = ConfirmPedidoCommand(pedido_id=id)
        result = await command_bus.dispatch(command)

        match result:
            case Ok(pedido_dto):
                return PedidoMutationResult(
                    success=True,
                    pedido=map_pedido_dto_to_type(pedido_dto),
                )
            case Err(error):
                return PedidoMutationResult(success=False, error=str(error))
