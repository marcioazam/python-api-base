"""CQRS Command and Query Handlers for PedidoExample.

**Feature: application-common-integration**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
"""

from decimal import Decimal
from typing import Any, Protocol

from application.common.dto import PaginatedResponse
from application.common.cqrs.events.event_bus import TypedEventBus
from application.common.cqrs.handlers import CommandHandler, QueryHandler
from application.examples.pedido.commands import (
    AddItemToPedidoCommand,
    CancelPedidoCommand,
    ConfirmPedidoCommand,
    CreatePedidoCommand,
)
from application.examples.pedido.dtos import PedidoExampleResponse
from application.examples.pedido.mappers import PedidoExampleMapper
from application.examples.pedido.queries import GetPedidoQuery, ListPedidosQuery
from application.examples.shared.errors import (
    NotFoundError,
    ValidationError,
)
from core.base.patterns.result import Err, Ok, Result
from domain.examples.pedido.entity import PedidoExample


class IPedidoRepository(Protocol):
    """Protocol for PedidoExample repository."""

    async def get(self, pedido_id: str) -> PedidoExample | None: ...
    async def create(self, entity: PedidoExample) -> PedidoExample: ...
    async def update(self, entity: PedidoExample) -> PedidoExample: ...
    async def get_all(self, **kwargs: Any) -> list[PedidoExample]: ...
    async def count(self, **kwargs: Any) -> int: ...


class IItemRepository(Protocol):
    """Protocol for ItemExample repository (for cross-entity validation)."""

    async def get(self, item_id: str) -> Any | None: ...


class CreatePedidoCommandHandler(
    CommandHandler[CreatePedidoCommand, PedidoExampleResponse]
):
    """Handler for CreatePedidoCommand."""

    def __init__(
        self,
        pedido_repository: IPedidoRepository,
        item_repository: IItemRepository,
        event_bus: TypedEventBus[Any] | None = None,
    ) -> None:
        self._pedido_repo = pedido_repository
        self._item_repo = item_repository
        self._event_bus = event_bus

    async def handle(
        self, command: CreatePedidoCommand
    ) -> Result[PedidoExampleResponse, Exception]:
        """Handle create pedido command."""
        pedido = PedidoExample.create(
            customer_id=command.customer_id,
            customer_name=command.customer_name,
            customer_email=command.customer_email,
            shipping_address=command.shipping_address,
            notes=command.notes,
            tenant_id=command.tenant_id,
            created_by=command.created_by,
        )

        for item_data in command.items:
            item = await self._item_repo.get(item_data.get("item_id", ""))
            if not item:
                return Err(NotFoundError("ItemExample", item_data.get("item_id", "")))
            if not item.is_available:
                return Err(ValidationError(f"Item '{item.name}' is not available"))

            pedido.add_item(
                item_id=item.id,
                item_name=item.name,
                quantity=item_data.get("quantity", 1),
                unit_price=item.price,
                discount=Decimal(str(item_data.get("discount", 0))),
            )

        saved = await self._pedido_repo.create(pedido)

        if self._event_bus:
            for event in saved.events:
                await self._event_bus.publish(event, raise_on_error=False)
            saved.clear_events()

        return Ok(PedidoExampleMapper.to_response(saved))


class AddItemToPedidoCommandHandler(
    CommandHandler[AddItemToPedidoCommand, PedidoExampleResponse]
):
    """Handler for AddItemToPedidoCommand."""

    def __init__(
        self,
        pedido_repository: IPedidoRepository,
        item_repository: IItemRepository,
        event_bus: TypedEventBus[Any] | None = None,
    ) -> None:
        self._pedido_repo = pedido_repository
        self._item_repo = item_repository
        self._event_bus = event_bus

    async def handle(
        self, command: AddItemToPedidoCommand
    ) -> Result[PedidoExampleResponse, Exception]:
        """Handle add item to pedido command."""
        pedido = await self._pedido_repo.get(command.pedido_id)
        if not pedido:
            return Err(NotFoundError("PedidoExample", command.pedido_id))

        if not pedido.can_be_modified:
            return Err(
                ValidationError(
                    f"Order in '{pedido.status.value}' status cannot be modified"
                )
            )

        item = await self._item_repo.get(command.item_id)
        if not item:
            return Err(NotFoundError("ItemExample", command.item_id))

        if not item.is_available:
            return Err(ValidationError(f"Item '{item.name}' is not available"))

        pedido.add_item(
            item_id=item.id,
            item_name=item.name,
            quantity=command.quantity,
            unit_price=item.price,
            discount=command.discount,
        )

        saved = await self._pedido_repo.update(pedido)

        if self._event_bus:
            for event in saved.events:
                await self._event_bus.publish(event, raise_on_error=False)
            saved.clear_events()

        return Ok(PedidoExampleMapper.to_response(saved))


class ConfirmPedidoCommandHandler(
    CommandHandler[ConfirmPedidoCommand, PedidoExampleResponse]
):
    """Handler for ConfirmPedidoCommand."""

    def __init__(
        self,
        repository: IPedidoRepository,
        event_bus: TypedEventBus[Any] | None = None,
    ) -> None:
        self._repo = repository
        self._event_bus = event_bus

    async def handle(
        self, command: ConfirmPedidoCommand
    ) -> Result[PedidoExampleResponse, Exception]:
        """Handle confirm pedido command."""
        pedido = await self._repo.get(command.pedido_id)
        if not pedido:
            return Err(NotFoundError("PedidoExample", command.pedido_id))

        try:
            pedido.confirm(command.confirmed_by)
        except ValueError as e:
            return Err(ValidationError(str(e)))

        saved = await self._repo.update(pedido)

        if self._event_bus:
            for event in saved.events:
                await self._event_bus.publish(event, raise_on_error=False)
            saved.clear_events()

        return Ok(PedidoExampleMapper.to_response(saved))


class CancelPedidoCommandHandler(
    CommandHandler[CancelPedidoCommand, PedidoExampleResponse]
):
    """Handler for CancelPedidoCommand."""

    def __init__(
        self,
        repository: IPedidoRepository,
        event_bus: TypedEventBus[Any] | None = None,
    ) -> None:
        self._repo = repository
        self._event_bus = event_bus

    async def handle(
        self, command: CancelPedidoCommand
    ) -> Result[PedidoExampleResponse, Exception]:
        """Handle cancel pedido command."""
        pedido = await self._repo.get(command.pedido_id)
        if not pedido:
            return Err(NotFoundError("PedidoExample", command.pedido_id))

        if not pedido.can_be_cancelled:
            return Err(
                ValidationError(
                    f"Order in '{pedido.status.value}' status cannot be cancelled"
                )
            )

        try:
            pedido.cancel(command.reason, command.cancelled_by)
        except ValueError as e:
            return Err(ValidationError(str(e)))

        saved = await self._repo.update(pedido)

        if self._event_bus:
            for event in saved.events:
                await self._event_bus.publish(event, raise_on_error=False)
            saved.clear_events()

        return Ok(PedidoExampleMapper.to_response(saved))


class GetPedidoQueryHandler(QueryHandler[GetPedidoQuery, PedidoExampleResponse]):
    """Handler for GetPedidoQuery."""

    def __init__(self, repository: IPedidoRepository) -> None:
        self._repo = repository

    async def handle(
        self, query: GetPedidoQuery
    ) -> Result[PedidoExampleResponse, Exception]:
        """Handle get pedido query."""
        pedido = await self._repo.get(query.pedido_id)
        if not pedido:
            return Err(NotFoundError("PedidoExample", query.pedido_id))
        return Ok(PedidoExampleMapper.to_response(pedido))


class ListPedidosQueryHandler(
    QueryHandler[ListPedidosQuery, PaginatedResponse[PedidoExampleResponse]]
):
    """Handler for ListPedidosQuery."""

    def __init__(self, repository: IPedidoRepository) -> None:
        self._repo = repository

    async def handle(
        self, query: ListPedidosQuery
    ) -> Result[PaginatedResponse[PedidoExampleResponse], Exception]:
        """Handle list pedidos query."""
        filters: dict[str, Any] = {}
        if query.customer_id:
            filters["customer_id"] = query.customer_id
        if query.status:
            filters["status"] = query.status
        if query.tenant_id:
            filters["tenant_id"] = query.tenant_id

        pedidos = await self._repo.get_all(
            skip=(query.page - 1) * query.size,
            limit=query.size,
            **filters,
        )
        total = await self._repo.count(**filters)

        return Ok(
            PaginatedResponse(
                items=PedidoExampleMapper.to_response_list(pedidos),
                total=total,
                page=query.page,
                size=query.size,
            )
        )
