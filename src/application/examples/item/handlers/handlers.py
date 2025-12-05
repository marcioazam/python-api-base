"""CQRS Command and Query Handlers for ItemExample.

**Feature: application-common-integration**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**
"""

from typing import Any, Protocol

from application.common.dto import PaginatedResponse
from application.common.cqrs.event_bus import TypedEventBus
from application.common.cqrs.handlers import CommandHandler, QueryHandler
from application.examples.item.commands import (
    CreateItemCommand,
    DeleteItemCommand,
    UpdateItemCommand,
)
from application.examples.item.dtos import ItemExampleResponse
from application.examples.item.mapper import ItemExampleMapper
from application.examples.item.queries import GetItemQuery, ListItemsQuery
from application.examples.shared.errors import (
    NotFoundError,
    ValidationError,
)
from core.base.patterns.result import Err, Ok, Result
from domain.examples.item.entity import ItemExample, Money


class IItemRepository(Protocol):
    """Protocol for ItemExample repository."""

    async def get(self, item_id: str) -> ItemExample | None: ...
    async def get_by_sku(self, sku: str) -> ItemExample | None: ...
    async def create(self, entity: ItemExample) -> ItemExample: ...
    async def update(self, entity: ItemExample) -> ItemExample: ...
    async def get_all(self, **kwargs: Any) -> list[ItemExample]: ...
    async def count(self, **kwargs: Any) -> int: ...


class CreateItemCommandHandler(CommandHandler[CreateItemCommand, ItemExampleResponse]):
    """Handler for CreateItemCommand."""

    def __init__(
        self,
        repository: IItemRepository,
        event_bus: TypedEventBus[Any] | None = None,
        mapper: ItemExampleMapper | None = None,
    ) -> None:
        self._repo = repository
        self._event_bus = event_bus
        self._mapper = mapper or ItemExampleMapper()

    async def handle(
        self, command: CreateItemCommand
    ) -> Result[ItemExampleResponse, Exception]:
        """Handle create item command."""
        existing = await self._repo.get_by_sku(command.sku)
        if existing:
            return Err(ValidationError(f"SKU '{command.sku}' already exists", "sku"))

        item = ItemExample.create(
            name=command.name,
            description=command.description,
            sku=command.sku,
            price=Money(command.price_amount, command.price_currency),
            quantity=command.quantity,
            category=command.category,
            tags=list(command.tags),
            created_by=command.created_by,
        )
        item.metadata = dict(command.metadata)

        saved = await self._repo.create(item)

        if self._event_bus:
            for event in saved.events:
                await self._event_bus.publish(event, raise_on_error=False)
            saved.clear_events()

        return Ok(self._mapper.to_dto(saved))


def _apply_update_command_fields(item: ItemExample, command: UpdateItemCommand) -> None:
    """Apply update command fields to item entity.

    Args:
        item: ItemExample entity to update.
        command: Update command with fields.
    """
    if command.name is not None:
        item.name = command.name
    if command.description is not None:
        item.description = command.description
    if command.price_amount is not None:
        currency = command.price_currency or item.price.currency
        item.price = Money(command.price_amount, currency)
    if command.quantity is not None:
        item.quantity = command.quantity
    if command.category is not None:
        item.category = command.category
    if command.tags is not None:
        item.tags = list(command.tags)
    if command.metadata is not None:
        item.metadata = dict(command.metadata)
    item.mark_updated_by(command.updated_by)


class UpdateItemCommandHandler(CommandHandler[UpdateItemCommand, ItemExampleResponse]):
    """Handler for UpdateItemCommand."""

    def __init__(
        self,
        repository: IItemRepository,
        event_bus: TypedEventBus[Any] | None = None,
        mapper: ItemExampleMapper | None = None,
    ) -> None:
        self._repo = repository
        self._event_bus = event_bus
        self._mapper = mapper or ItemExampleMapper()

    async def handle(
        self, command: UpdateItemCommand
    ) -> Result[ItemExampleResponse, Exception]:
        """Handle update item command."""
        item = await self._repo.get(command.item_id)
        if not item:
            return Err(NotFoundError("ItemExample", command.item_id))

        _apply_update_command_fields(item, command)
        saved = await self._repo.update(item)

        if self._event_bus:
            for event in saved.events:
                await self._event_bus.publish(event, raise_on_error=False)
            saved.clear_events()

        return Ok(self._mapper.to_dto(saved))


class DeleteItemCommandHandler(CommandHandler[DeleteItemCommand, bool]):
    """Handler for DeleteItemCommand."""

    def __init__(
        self,
        repository: IItemRepository,
        event_bus: TypedEventBus[Any] | None = None,
    ) -> None:
        self._repo = repository
        self._event_bus = event_bus

    async def handle(self, command: DeleteItemCommand) -> Result[bool, Exception]:
        """Handle delete item command."""
        item = await self._repo.get(command.item_id)
        if not item:
            return Err(NotFoundError("ItemExample", command.item_id))

        item.soft_delete(command.deleted_by)
        await self._repo.update(item)

        if self._event_bus:
            for event in item.events:
                await self._event_bus.publish(event, raise_on_error=False)
            item.clear_events()

        return Ok(True)


class GetItemQueryHandler(QueryHandler[GetItemQuery, ItemExampleResponse]):
    """Handler for GetItemQuery."""

    def __init__(
        self,
        repository: IItemRepository,
        mapper: ItemExampleMapper | None = None,
    ) -> None:
        self._repo = repository
        self._mapper = mapper or ItemExampleMapper()

    async def handle(
        self, query: GetItemQuery
    ) -> Result[ItemExampleResponse, Exception]:
        """Handle get item query."""
        item = await self._repo.get(query.item_id)
        if not item:
            return Err(NotFoundError("ItemExample", query.item_id))
        return Ok(self._mapper.to_dto(item))


class ListItemsQueryHandler(
    QueryHandler[ListItemsQuery, PaginatedResponse[ItemExampleResponse]]
):
    """Handler for ListItemsQuery."""

    def __init__(
        self,
        repository: IItemRepository,
        mapper: ItemExampleMapper | None = None,
    ) -> None:
        self._repo = repository
        self._mapper = mapper or ItemExampleMapper()

    async def handle(
        self, query: ListItemsQuery
    ) -> Result[PaginatedResponse[ItemExampleResponse], Exception]:
        """Handle list items query."""
        filters = {}
        if query.category:
            filters["category"] = query.category
        if query.status:
            filters["status"] = query.status

        items = await self._repo.get_all(
            skip=(query.page - 1) * query.size,
            limit=query.size,
            **filters,
        )
        total = await self._repo.count(**filters)

        return Ok(
            PaginatedResponse(
                items=self._mapper.to_dto_list(items),
                total=total,
                page=query.page,
                size=query.size,
            )
        )
