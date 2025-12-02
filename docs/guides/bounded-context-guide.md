# Guia: Criando um Bounded Context

Este guia descreve o processo passo a passo para criar um novo bounded context no Python API Base.

## Visão Geral

Um bounded context encapsula um domínio de negócio específico. Cada bounded context tem:
- Entidades e Value Objects (Domain)
- Use Cases e DTOs (Application)
- Repositórios e Serviços (Infrastructure)
- Endpoints de API (Interface)

## 1. Domain Layer

### 1.1 Criar Entidade

```python
# src/domain/orders/entities.py
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

@dataclass
class Order:
    id: str
    customer_id: str
    items: list["OrderItem"]
    total: Decimal
    status: "OrderStatus"
    created_at: datetime
    updated_at: datetime | None = None

@dataclass
class OrderItem:
    product_id: str
    quantity: int
    unit_price: Decimal

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity
```

### 1.2 Criar Value Objects

```python
# src/domain/orders/value_objects.py
from dataclasses import dataclass
from enum import Enum

class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "BRL"

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Currency mismatch")
        return Money(self.amount + other.amount, self.currency)
```

### 1.3 Criar Repository Interface

```python
# src/domain/orders/repository.py
from typing import Protocol
from core.protocols import AsyncRepository
from .entities import Order

class IOrderRepository(AsyncRepository[Order, str], Protocol):
    async def get_by_customer(
        self,
        customer_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Order]: ...

    async def get_by_status(
        self,
        status: OrderStatus,
    ) -> list[Order]: ...
```

### 1.4 Criar Domain Events

```python
# src/domain/orders/events.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class OrderCreated:
    order_id: str
    customer_id: str
    total: Decimal
    timestamp: datetime

@dataclass
class OrderStatusChanged:
    order_id: str
    old_status: OrderStatus
    new_status: OrderStatus
    timestamp: datetime
```

## 2. Application Layer

### 2.1 Criar DTOs

```python
# src/application/orders/dtos.py
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal

class OrderItemDTO(BaseModel):
    product_id: str
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(gt=0)

class CreateOrderDTO(BaseModel):
    customer_id: str
    items: list[OrderItemDTO] = Field(min_length=1)

class OrderDTO(BaseModel):
    id: str
    customer_id: str
    items: list[OrderItemDTO]
    total: Decimal
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

### 2.2 Criar Commands

```python
# src/application/orders/commands/create_order.py
from dataclasses import dataclass
from result import Result, Ok, Err
from application.common.cqrs import Command
from domain.orders.entities import Order, OrderItem
from domain.orders.value_objects import OrderStatus

@dataclass
class CreateOrderCommand(Command[Order]):
    customer_id: str
    items: list[dict]

    async def execute(
        self,
        repository: IOrderRepository,
    ) -> Result[Order, str]:
        if not self.items:
            return Err("Order must have at least one item")

        order_items = [
            OrderItem(
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=Decimal(item["unit_price"]),
            )
            for item in self.items
        ]

        total = sum(item.subtotal for item in order_items)

        order = Order(
            id=generate_ulid(),
            customer_id=self.customer_id,
            items=order_items,
            total=total,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        created = await repository.create(order)
        return Ok(created)
```

### 2.3 Criar Queries

```python
# src/application/orders/queries/get_order.py
from dataclasses import dataclass
from application.common.cqrs import Query
from application.orders.dtos import OrderDTO
from application.orders.mappers import OrderMapper

@dataclass
class GetOrderQuery(Query[OrderDTO | None]):
    order_id: str
    cacheable: bool = True
    cache_ttl: int = 60

    async def execute(
        self,
        repository: IOrderRepository,
    ) -> OrderDTO | None:
        order = await repository.get(self.order_id)
        if order is None:
            return None
        return OrderMapper.to_dto(order)
```

### 2.4 Criar Mapper

```python
# src/application/orders/mappers.py
from domain.orders.entities import Order
from .dtos import OrderDTO, OrderItemDTO

class OrderMapper:
    @staticmethod
    def to_dto(order: Order) -> OrderDTO:
        return OrderDTO(
            id=order.id,
            customer_id=order.customer_id,
            items=[
                OrderItemDTO(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
                for item in order.items
            ],
            total=order.total,
            status=order.status.value,
            created_at=order.created_at,
        )
```

## 3. Infrastructure Layer

### 3.1 Criar SQLAlchemy Model

```python
# src/infrastructure/db/models/order.py
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from decimal import Decimal

class OrderModel(SQLModel, table=True):
    __tablename__ = "orders"

    id: str = Field(primary_key=True)
    customer_id: str = Field(index=True)
    total: Decimal
    status: str
    created_at: datetime
    updated_at: datetime | None = None

    items: list["OrderItemModel"] = Relationship(back_populates="order")

class OrderItemModel(SQLModel, table=True):
    __tablename__ = "order_items"

    id: str = Field(primary_key=True)
    order_id: str = Field(foreign_key="orders.id")
    product_id: str
    quantity: int
    unit_price: Decimal

    order: OrderModel = Relationship(back_populates="items")
```

### 3.2 Criar Repository Implementation

```python
# src/infrastructure/db/repositories/order_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from domain.orders.repository import IOrderRepository
from domain.orders.entities import Order
from domain.orders.value_objects import OrderStatus
from ..models.order import OrderModel

class OrderRepository(IOrderRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, id: str) -> Order | None:
        model = await self._session.get(OrderModel, id)
        return self._to_entity(model) if model else None

    async def get_by_customer(
        self,
        customer_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Order]:
        result = await self._session.execute(
            select(OrderModel)
            .where(OrderModel.customer_id == customer_id)
            .offset(skip)
            .limit(limit)
        )
        return [self._to_entity(m) for m in result.scalars()]

    async def create(self, order: Order) -> Order:
        model = self._to_model(order)
        self._session.add(model)
        await self._session.flush()
        return order

    def _to_entity(self, model: OrderModel) -> Order:
        # Convert model to entity
        ...

    def _to_model(self, entity: Order) -> OrderModel:
        # Convert entity to model
        ...
```

## 4. Interface Layer

### 4.1 Criar Router

```python
# src/interface/v1/orders.py
from fastapi import APIRouter, Depends, HTTPException
from application.orders.dtos import CreateOrderDTO, OrderDTO
from application.orders.commands.create_order import CreateOrderCommand
from application.orders.queries.get_order import GetOrderQuery

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=OrderDTO, status_code=201)
async def create_order(
    data: CreateOrderDTO,
    repository: IOrderRepository = Depends(get_order_repository),
) -> OrderDTO:
    command = CreateOrderCommand(
        customer_id=data.customer_id,
        items=[item.dict() for item in data.items],
    )
    result = await command.execute(repository)

    if result.is_err():
        raise HTTPException(400, detail=result.error)

    return OrderMapper.to_dto(result.value)

@router.get("/{order_id}", response_model=OrderDTO)
async def get_order(
    order_id: str,
    repository: IOrderRepository = Depends(get_order_repository),
) -> OrderDTO:
    query = GetOrderQuery(order_id=order_id)
    order = await query.execute(repository)

    if order is None:
        raise HTTPException(404, detail="Order not found")

    return order
```

### 4.2 Registrar Router

```python
# src/interface/router.py
from .v1.orders import router as orders_router

app.include_router(orders_router, prefix="/api/v1")
```

## 5. Testes

### 5.1 Unit Tests

```python
# tests/unit/domain/orders/test_order.py
def test_order_item_subtotal():
    item = OrderItem(
        product_id="prod-1",
        quantity=3,
        unit_price=Decimal("10.00"),
    )
    assert item.subtotal == Decimal("30.00")
```

### 5.2 Integration Tests

```python
# tests/integration/test_orders.py
@pytest.mark.asyncio
async def test_create_order(client: AsyncClient):
    response = await client.post(
        "/api/v1/orders",
        json={
            "customer_id": "cust-1",
            "items": [
                {"product_id": "prod-1", "quantity": 2, "unit_price": "10.00"}
            ],
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
```

## Checklist

- [ ] Domain: Entidade criada
- [ ] Domain: Value Objects criados
- [ ] Domain: Repository interface definida
- [ ] Domain: Events definidos
- [ ] Application: DTOs criados
- [ ] Application: Commands implementados
- [ ] Application: Queries implementadas
- [ ] Application: Mapper criado
- [ ] Infrastructure: Model SQLAlchemy criado
- [ ] Infrastructure: Repository implementado
- [ ] Infrastructure: Migration criada
- [ ] Interface: Router criado
- [ ] Interface: Router registrado
- [ ] Tests: Unit tests escritos
- [ ] Tests: Integration tests escritos
