"""Seed script for Example System demo data.

Creates sample ItemExample and PedidoExample data for testing.

**Feature: example-system-demo**

Usage:
    python -m scripts.seed_examples
"""

import asyncio
import logging
from decimal import Decimal
from uuid import uuid4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_items(session) -> list[str]:
    """Create sample items."""
    from domain.examples.item_example import ItemExample, Money, ItemExampleStatus
    from infrastructure.db.repositories.examples import ItemExampleRepository

    repo = ItemExampleRepository(session)

    items_data = [
        {
            "name": "Widget Pro",
            "description": "Professional grade widget for enterprise use",
            "sku": "WDG-PRO-001",
            "price": Money(Decimal("199.90"), "BRL"),
            "quantity": 100,
            "category": "electronics",
            "tags": ["professional", "enterprise"],
        },
        {
            "name": "Widget Basic",
            "description": "Entry-level widget for beginners",
            "sku": "WDG-BSC-001",
            "price": Money(Decimal("49.90"), "BRL"),
            "quantity": 500,
            "category": "electronics",
            "tags": ["basic", "starter"],
        },
        {
            "name": "Gadget X",
            "description": "Next generation gadget with AI features",
            "sku": "GDG-X-001",
            "price": Money(Decimal("599.00"), "BRL"),
            "quantity": 50,
            "category": "electronics",
            "tags": ["ai", "premium"],
        },
        {
            "name": "Accessory Pack",
            "description": "Complete accessory pack for widgets",
            "sku": "ACC-PCK-001",
            "price": Money(Decimal("79.90"), "BRL"),
            "quantity": 200,
            "category": "accessories",
            "tags": ["bundle", "accessories"],
        },
        {
            "name": "Premium Cable",
            "description": "High-speed data transfer cable",
            "sku": "CBL-PRM-001",
            "price": Money(Decimal("29.90"), "BRL"),
            "quantity": 1000,
            "category": "accessories",
            "tags": ["cable", "data"],
        },
    ]

    item_ids = []
    for data in items_data:
        existing = await repo.get_by_sku(data["sku"])
        if existing:
            logger.info(f"Item {data['sku']} already exists, skipping")
            item_ids.append(existing.id)
            continue

        item = ItemExample.create(
            name=data["name"],
            description=data["description"],
            sku=data["sku"],
            price=data["price"],
            quantity=data["quantity"],
            category=data["category"],
            tags=data["tags"],
            created_by="seed_script",
        )
        saved = await repo.create(item)
        item_ids.append(saved.id)
        logger.info(f"Created item: {saved.name} ({saved.sku})")

    return item_ids


async def seed_pedidos(session, item_ids: list[str]) -> None:
    """Create sample orders."""
    from domain.examples.pedido_example import PedidoExample
    from infrastructure.db.repositories.examples import (
        ItemExampleRepository,
        PedidoExampleRepository,
    )

    item_repo = ItemExampleRepository(session)
    pedido_repo = PedidoExampleRepository(session)

    customers = [
        {
            "customer_id": "CUST-001",
            "customer_name": "João Silva",
            "customer_email": "joao.silva@example.com",
            "shipping_address": "Rua das Flores, 123 - São Paulo, SP",
        },
        {
            "customer_id": "CUST-002",
            "customer_name": "Maria Santos",
            "customer_email": "maria.santos@example.com",
            "shipping_address": "Av. Brasil, 456 - Rio de Janeiro, RJ",
        },
        {
            "customer_id": "CUST-003",
            "customer_name": "Tech Corp LTDA",
            "customer_email": "compras@techcorp.com.br",
            "shipping_address": "Rua da Tecnologia, 789 - Curitiba, PR",
            "tenant_id": "tenant-001",
        },
    ]

    for i, customer in enumerate(customers):
        pedido = PedidoExample.create(
            customer_id=customer["customer_id"],
            customer_name=customer["customer_name"],
            customer_email=customer["customer_email"],
            shipping_address=customer["shipping_address"],
            tenant_id=customer.get("tenant_id"),
            created_by="seed_script",
        )

        # Add some items
        if item_ids:
            # Add first item
            item1 = await item_repo.get(item_ids[0])
            if item1:
                pedido.add_item(
                    item_id=item1.id,
                    item_name=item1.name,
                    quantity=2,
                    unit_price=item1.price,
                )

            # Add second item if exists
            if len(item_ids) > 1:
                item2 = await item_repo.get(item_ids[1])
                if item2:
                    pedido.add_item(
                        item_id=item2.id,
                        item_name=item2.name,
                        quantity=1,
                        unit_price=item2.price,
                        discount=Decimal("10"),
                    )

        # Confirm some orders
        if i == 0:
            pedido.confirm("seed_script")

        saved = await pedido_repo.create(pedido)
        logger.info(
            f"Created order: {saved.id} for {customer['customer_name']} "
            f"(status: {saved.status.value}, total: {saved.total.amount})"
        )


async def main() -> None:
    """Main seed function."""
    logger.info("Starting Example System seed...")

    try:
        from infrastructure.db.session import get_async_session

        async with get_async_session() as session:
            item_ids = await seed_items(session)
            await seed_pedidos(session, item_ids)
            await session.commit()

        logger.info("Seed completed successfully!")

    except ImportError:
        logger.warning(
            "Could not import database session. "
            "Running with mock data for demonstration."
        )
        logger.info("In production, configure DATABASE_URL environment variable.")


if __name__ == "__main__":
    asyncio.run(main())
