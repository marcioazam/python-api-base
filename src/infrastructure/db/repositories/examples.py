"""Repositories for ItemExample and PedidoExample.

Demonstrates:
- Generic repository implementation
- SQLModel/SQLAlchemy async operations
- Soft delete handling
- Query filtering
- Entity mapping

**Feature: example-system-demo**
"""

import logging

from sqlalchemy import select, and_, false
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.examples.item_example import ItemExample, ItemExampleStatus, Money
from domain.examples.pedido_example import (
    PedidoExample,
    PedidoItemExample,
    PedidoStatus,
)
from infrastructure.db.models.examples import (
    ItemExampleModel,
    PedidoExampleModel,
    PedidoItemExampleModel,
)

logger = logging.getLogger(__name__)


class ItemExampleRepository:
    """Repository for ItemExample persistence.

    Demonstrates:
    - Async SQLAlchemy operations
    - Entity to model mapping
    - Soft delete filtering
    - Query builder usage
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: ItemExampleModel) -> ItemExample:
        """Map database model to domain entity."""
        entity = ItemExample(
            id=model.id,
            name=model.name,
            description=model.description,
            sku=model.sku,
            price=Money(model.price_amount, model.price_currency),
            quantity=model.quantity,
            status=ItemExampleStatus(model.status),
            category=model.category,
            tags=model.tags or [],
            metadata=model.metadata or {},
            created_by=model.created_by,
            updated_by=model.updated_by,
        )
        entity.created_at = model.created_at
        entity.updated_at = model.updated_at
        entity.is_deleted = model.is_deleted
        entity.deleted_at = model.deleted_at
        return entity

    def _to_model(self, entity: ItemExample) -> ItemExampleModel:
        """Map domain entity to database model."""
        return ItemExampleModel(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            sku=entity.sku,
            price_amount=entity.price.amount,
            price_currency=entity.price.currency,
            quantity=entity.quantity,
            status=entity.status.value,
            category=entity.category,
            tags=entity.tags,
            metadata=entity.metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
        )

    async def get(self, item_id: str) -> ItemExample | None:
        """Get item by ID."""
        stmt = select(ItemExampleModel).where(
            and_(
                ItemExampleModel.id == item_id,
                ItemExampleModel.is_deleted.is_(false()),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_sku(self, sku: str) -> ItemExample | None:
        """Get item by SKU."""
        stmt = select(ItemExampleModel).where(
            and_(
                ItemExampleModel.sku == sku,
                ItemExampleModel.is_deleted.is_(false()),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def create(self, entity: ItemExample) -> ItemExample:
        """Create a new item."""
        model = self._to_model(entity)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        logger.debug(f"Created ItemExample: {model.id}")
        return self._to_entity(model)

    async def update(self, entity: ItemExample) -> ItemExample:
        """Update an existing item."""
        stmt = select(ItemExampleModel).where(ItemExampleModel.id == entity.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            model.name = entity.name
            model.description = entity.description
            model.sku = entity.sku
            model.price_amount = entity.price.amount
            model.price_currency = entity.price.currency
            model.quantity = entity.quantity
            model.status = entity.status.value
            model.category = entity.category
            model.tags = entity.tags
            model.metadata = entity.metadata
            model.updated_at = entity.updated_at
            model.updated_by = entity.updated_by
            model.is_deleted = entity.is_deleted
            model.deleted_at = entity.deleted_at

            await self._session.commit()
            await self._session.refresh(model)
            logger.debug(f"Updated ItemExample: {model.id}")
            return self._to_entity(model)

        raise ValueError(f"ItemExample {entity.id} not found")

    async def delete(self, item_id: str) -> bool:
        """Hard delete an item (use soft delete via update instead)."""
        stmt = select(ItemExampleModel).where(ItemExampleModel.id == item_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            await self._session.delete(model)
            await self._session.commit()
            return True
        return False

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        status: str | None = None,
    ) -> list[ItemExample]:
        """Get all items with pagination and filtering."""
        conditions = [ItemExampleModel.is_deleted == False]

        if category:
            conditions.append(ItemExampleModel.category == category)
        if status:
            conditions.append(ItemExampleModel.status == status)

        stmt = (
            select(ItemExampleModel)
            .where(and_(*conditions))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .order_by(ItemExampleModel.created_at.desc())
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]


class PedidoExampleRepository:
    """Repository for PedidoExample persistence.

    Demonstrates:
    - Aggregate root persistence
    - Child entity handling
    - Eager loading relationships
    - Multi-tenant filtering
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: PedidoExampleModel) -> PedidoExample:
        """Map database model to domain entity."""
        entity = PedidoExample(
            id=model.id,
            customer_id=model.customer_id,
            customer_name=model.customer_name,
            customer_email=model.customer_email,
            status=PedidoStatus(model.status),
            shipping_address=model.shipping_address,
            notes=model.notes,
            tenant_id=model.tenant_id,
            metadata=model.metadata or {},
            created_by=model.created_by,
            updated_by=model.updated_by,
        )
        entity.created_at = model.created_at
        entity.updated_at = model.updated_at
        entity.is_deleted = model.is_deleted
        entity.deleted_at = model.deleted_at

        # Map items
        entity.items = [
            PedidoItemExample(
                id=item.id,
                pedido_id=item.pedido_id,
                item_id=item.item_id,
                item_name=item.item_name,
                quantity=item.quantity,
                unit_price=Money(item.unit_price_amount, item.unit_price_currency),
                discount=item.discount,
            )
            for item in model.items
        ]

        return entity

    def _to_model(self, entity: PedidoExample) -> PedidoExampleModel:
        """Map domain entity to database model."""
        model = PedidoExampleModel(
            id=entity.id,
            customer_id=entity.customer_id,
            customer_name=entity.customer_name,
            customer_email=entity.customer_email,
            status=entity.status.value,
            shipping_address=entity.shipping_address,
            notes=entity.notes,
            tenant_id=entity.tenant_id,
            metadata=entity.metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
        )

        model.items = [
            PedidoItemExampleModel(
                id=item.id,
                pedido_id=item.pedido_id,
                item_id=item.item_id,
                item_name=item.item_name,
                quantity=item.quantity,
                unit_price_amount=item.unit_price.amount,
                unit_price_currency=item.unit_price.currency,
                discount=item.discount,
            )
            for item in entity.items
        ]

        return model

    async def get(self, pedido_id: str) -> PedidoExample | None:
        """Get order by ID with items."""
        stmt = (
            select(PedidoExampleModel)
            .where(
                and_(
                    PedidoExampleModel.id == pedido_id,
                    PedidoExampleModel.is_deleted == False,
                )
            )
            .options(selectinload(PedidoExampleModel.items))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def create(self, entity: PedidoExample) -> PedidoExample:
        """Create a new order with items."""
        model = self._to_model(entity)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model, ["items"])
        logger.debug(f"Created PedidoExample: {model.id}")
        return self._to_entity(model)

    async def update(self, entity: PedidoExample) -> PedidoExample:
        """Update an order."""
        stmt = (
            select(PedidoExampleModel)
            .where(PedidoExampleModel.id == entity.id)
            .options(selectinload(PedidoExampleModel.items))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            model.customer_name = entity.customer_name
            model.customer_email = entity.customer_email
            model.status = entity.status.value
            model.shipping_address = entity.shipping_address
            model.notes = entity.notes
            model.metadata = entity.metadata
            model.updated_at = entity.updated_at
            model.updated_by = entity.updated_by
            model.is_deleted = entity.is_deleted
            model.deleted_at = entity.deleted_at

            # Sync items - remove old, add new
            model.items.clear()
            for item in entity.items:
                model.items.append(
                    PedidoItemExampleModel(
                        id=item.id,
                        pedido_id=item.pedido_id,
                        item_id=item.item_id,
                        item_name=item.item_name,
                        quantity=item.quantity,
                        unit_price_amount=item.unit_price.amount,
                        unit_price_currency=item.unit_price.currency,
                        discount=item.discount,
                    )
                )

            await self._session.commit()
            await self._session.refresh(model, ["items"])
            logger.debug(f"Updated PedidoExample: {model.id}")
            return self._to_entity(model)

        raise ValueError(f"PedidoExample {entity.id} not found")

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        customer_id: str | None = None,
        status: str | None = None,
        tenant_id: str | None = None,
    ) -> list[PedidoExample]:
        """Get all orders with pagination and filtering."""
        conditions = [PedidoExampleModel.is_deleted == False]

        if customer_id:
            conditions.append(PedidoExampleModel.customer_id == customer_id)
        if status:
            conditions.append(PedidoExampleModel.status == status)
        if tenant_id:
            conditions.append(PedidoExampleModel.tenant_id == tenant_id)

        stmt = (
            select(PedidoExampleModel)
            .where(and_(*conditions))
            .options(selectinload(PedidoExampleModel.items))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .order_by(PedidoExampleModel.created_at.desc())
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]
