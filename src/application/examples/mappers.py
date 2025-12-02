"""Mappers for ItemExample and PedidoExample.

Demonstrates:
- Generic mapper pattern
- Entity to DTO transformation
- Batch mapping

**Feature: example-system-demo**
"""

from domain.examples.item_example import ItemExample
from domain.examples.pedido_example import PedidoExample, PedidoItemExample
from application.examples.dtos import (
    ItemExampleResponse,
    PedidoExampleResponse,
    PedidoItemResponse,
    MoneyDTO,
)


class ItemExampleMapper:
    """Mapper for ItemExample entity to DTOs."""

    @staticmethod
    def to_response(entity: ItemExample) -> ItemExampleResponse:
        """Map ItemExample entity to response DTO."""
        return ItemExampleResponse(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            sku=entity.sku,
            price=MoneyDTO(
                amount=entity.price.amount,
                currency=entity.price.currency,
            ),
            quantity=entity.quantity,
            status=entity.status.value,
            category=entity.category,
            tags=entity.tags,
            is_available=entity.is_available,
            total_value=MoneyDTO(
                amount=entity.total_value.amount,
                currency=entity.total_value.currency,
            ),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
        )

    @staticmethod
    def to_response_list(entities: list[ItemExample]) -> list[ItemExampleResponse]:
        """Map list of entities to response DTOs."""
        return [ItemExampleMapper.to_response(e) for e in entities]


class PedidoItemMapper:
    """Mapper for PedidoItemExample entity to DTOs."""

    @staticmethod
    def to_response(entity: PedidoItemExample) -> PedidoItemResponse:
        """Map PedidoItemExample entity to response DTO."""
        return PedidoItemResponse(
            id=entity.id,
            item_id=entity.item_id,
            item_name=entity.item_name,
            quantity=entity.quantity,
            unit_price=MoneyDTO(
                amount=entity.unit_price.amount,
                currency=entity.unit_price.currency,
            ),
            discount=entity.discount,
            subtotal=MoneyDTO(
                amount=entity.subtotal.amount,
                currency=entity.subtotal.currency,
            ),
            total=MoneyDTO(
                amount=entity.total.amount,
                currency=entity.total.currency,
            ),
        )


class PedidoExampleMapper:
    """Mapper for PedidoExample entity to DTOs."""

    @staticmethod
    def to_response(entity: PedidoExample) -> PedidoExampleResponse:
        """Map PedidoExample entity to response DTO."""
        return PedidoExampleResponse(
            id=entity.id,
            customer_id=entity.customer_id,
            customer_name=entity.customer_name,
            customer_email=entity.customer_email,
            status=entity.status.value,
            shipping_address=entity.shipping_address,
            notes=entity.notes,
            items=[PedidoItemMapper.to_response(i) for i in entity.items],
            items_count=entity.items_count,
            subtotal=MoneyDTO(
                amount=entity.subtotal.amount,
                currency=entity.subtotal.currency,
            ),
            total_discount=MoneyDTO(
                amount=entity.total_discount.amount,
                currency=entity.total_discount.currency,
            ),
            total=MoneyDTO(
                amount=entity.total.amount,
                currency=entity.total.currency,
            ),
            can_be_modified=entity.can_be_modified,
            can_be_cancelled=entity.can_be_cancelled,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
        )

    @staticmethod
    def to_response_list(
        entities: list[PedidoExample],
    ) -> list[PedidoExampleResponse]:
        """Map list of entities to response DTOs."""
        return [PedidoExampleMapper.to_response(e) for e in entities]
