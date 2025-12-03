# Bounded Context Guide

## Overview

This guide explains how to create a new bounded context in Python API Base following DDD principles.

## Step 1: Plan the Bounded Context

Before coding, define:

1. **Context Name**: Clear, domain-specific name
2. **Entities**: Main domain objects
3. **Value Objects**: Immutable attributes
4. **Aggregates**: Transactional boundaries
5. **Domain Events**: Important state changes
6. **Repository Interface**: Data access contract

## Step 2: Create Domain Layer

### Directory Structure

```
src/domain/{context_name}/
├── __init__.py
├── entities.py       # Entity definitions
├── aggregates.py     # Aggregate roots (if different from entities)
├── value_objects.py  # Value objects
├── events.py         # Domain events
├── repositories.py   # Repository interface
├── services.py       # Domain services (optional)
└── specifications.py # Business rule specifications
```

### Entity Definition

```python
# src/domain/products/entities.py
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from src.core.base.domain import Entity
from src.core.types import ULID, generate_ulid

@dataclass
class Product(Entity[ULID]):
    """Product entity."""
    
    id: ULID = field(default_factory=generate_ulid)
    name: str = ""
    description: str | None = None
    price: Decimal = Decimal("0")
    sku: str = ""
    category_id: ULID | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
    
    def update_price(self, new_price: Decimal) -> None:
        """Update product price."""
        if new_price < 0:
            raise ValidationError("Price cannot be negative")
        self.price = new_price
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Deactivate product."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
```

### Value Objects

```python
# src/domain/products/value_objects.py
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class SKU:
    """Stock Keeping Unit value object."""
    
    value: str
    
    def __post_init__(self):
        if not self.value or len(self.value) < 3:
            raise ValidationError("SKU must be at least 3 characters")
        if not self.value.isalnum():
            raise ValidationError("SKU must be alphanumeric")

@dataclass(frozen=True)
class Price:
    """Price value object."""
    
    amount: Decimal
    currency: str = "USD"
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValidationError("Price cannot be negative")
    
    def apply_discount(self, percentage: Decimal) -> "Price":
        """Apply percentage discount."""
        discount = self.amount * (percentage / 100)
        return Price(self.amount - discount, self.currency)
```

### Domain Events

```python
# src/domain/products/events.py
from dataclasses import dataclass
from decimal import Decimal

from src.core.base.events import DomainEvent

@dataclass
class ProductCreatedEvent(DomainEvent):
    """Raised when a product is created."""
    product_id: str
    name: str
    sku: str
    aggregate_type: str = "Product"

@dataclass
class ProductPriceChangedEvent(DomainEvent):
    """Raised when product price changes."""
    product_id: str
    old_price: Decimal
    new_price: Decimal
    aggregate_type: str = "Product"

@dataclass
class ProductDeactivatedEvent(DomainEvent):
    """Raised when a product is deactivated."""
    product_id: str
    aggregate_type: str = "Product"
```

### Repository Interface

```python
# src/domain/products/repositories.py
from typing import Protocol

from src.core.protocols import IQueryableRepository
from src.core.types import ULID
from .entities import Product

class IProductRepository(IQueryableRepository[Product, ULID], Protocol):
    """Product repository interface."""
    
    async def get_by_sku(self, sku: str) -> Product | None:
        """Get product by SKU."""
        ...
    
    async def get_by_category(self, category_id: ULID) -> list[Product]:
        """Get products by category."""
        ...
    
    async def get_active_products(self) -> list[Product]:
        """Get all active products."""
        ...
```

## Step 3: Create Application Layer

### Directory Structure

```
src/application/{context_name}/
├── __init__.py
├── commands/
│   ├── __init__.py
│   └── product_commands.py
├── queries/
│   ├── __init__.py
│   └── product_queries.py
├── dtos.py
└── mapper.py
```

### DTOs

```python
# src/application/products/dtos.py
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime

class ProductCreateDTO(BaseModel):
    """DTO for creating a product."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    price: Decimal = Field(..., ge=0)
    sku: str = Field(..., min_length=3, max_length=50)
    category_id: str | None = None

class ProductUpdateDTO(BaseModel):
    """DTO for updating a product."""
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    price: Decimal | None = Field(None, ge=0)

class ProductResponseDTO(BaseModel):
    """DTO for product response."""
    id: str
    name: str
    description: str | None
    price: Decimal
    sku: str
    category_id: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None
    
    @classmethod
    def from_entity(cls, product: Product) -> "ProductResponseDTO":
        return cls(
            id=str(product.id),
            name=product.name,
            description=product.description,
            price=product.price,
            sku=product.sku,
            category_id=str(product.category_id) if product.category_id else None,
            is_active=product.is_active,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )
```

### Commands

```python
# src/application/products/commands/product_commands.py
from dataclasses import dataclass

from src.core.base.cqrs import Command
from src.core.types.result_types import Result, Ok, Err
from src.domain.products.entities import Product
from src.domain.products.repositories import IProductRepository

@dataclass
class CreateProductCommand(Command[Product, str]):
    """Create a new product."""
    name: str
    description: str | None
    price: Decimal
    sku: str
    category_id: str | None
    
    repository: IProductRepository
    event_bus: IEventBus
    
    async def execute(self) -> Result[Product, str]:
        # Check SKU uniqueness
        existing = await self.repository.get_by_sku(self.sku)
        if existing:
            return Err(f"Product with SKU {self.sku} already exists")
        
        # Create product
        product = Product(
            name=self.name,
            description=self.description,
            price=self.price,
            sku=self.sku,
            category_id=ULID(self.category_id) if self.category_id else None,
        )
        
        # Persist
        await self.repository.add(product)
        
        # Publish events
        await self.event_bus.publish(
            ProductCreatedEvent(
                product_id=str(product.id),
                name=product.name,
                sku=product.sku,
            )
        )
        
        return Ok(product)
```

## Step 4: Create Infrastructure Layer

### Repository Implementation

```python
# src/infrastructure/db/repositories/product_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.infrastructure.db.repositories.base import QueryableRepository
from src.domain.products.entities import Product
from src.domain.products.repositories import IProductRepository
from src.core.types import ULID

class ProductRepository(QueryableRepository[Product, ULID], IProductRepository):
    """SQLAlchemy product repository."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Product)
    
    async def get_by_sku(self, sku: str) -> Product | None:
        result = await self._session.execute(
            select(Product).where(Product.sku == sku)
        )
        return result.scalar_one_or_none()
    
    async def get_by_category(self, category_id: ULID) -> list[Product]:
        result = await self._session.execute(
            select(Product).where(Product.category_id == category_id)
        )
        return list(result.scalars().all())
    
    async def get_active_products(self) -> list[Product]:
        result = await self._session.execute(
            select(Product).where(Product.is_active == True)
        )
        return list(result.scalars().all())
```

## Step 5: Create Interface Layer

### Router

```python
# src/interface/v1/products_router.py
from fastapi import APIRouter, Depends, HTTPException

from src.application.products.dtos import (
    ProductCreateDTO,
    ProductUpdateDTO,
    ProductResponseDTO,
)
from src.application.products.commands import CreateProductCommand
from src.interface.dependencies import get_product_repository, get_event_bus

router = APIRouter(prefix="/products", tags=["Products"])

@router.post("", response_model=ProductResponseDTO, status_code=201)
async def create_product(
    data: ProductCreateDTO,
    repository: IProductRepository = Depends(get_product_repository),
    event_bus: IEventBus = Depends(get_event_bus),
):
    """Create a new product."""
    command = CreateProductCommand(
        name=data.name,
        description=data.description,
        price=data.price,
        sku=data.sku,
        category_id=data.category_id,
        repository=repository,
        event_bus=event_bus,
    )
    
    result = await command.execute()
    
    if result.is_err:
        raise HTTPException(status_code=400, detail=result.unwrap_err())
    
    return ProductResponseDTO.from_entity(result.unwrap())

@router.get("/{product_id}", response_model=ProductResponseDTO)
async def get_product(
    product_id: str,
    repository: IProductRepository = Depends(get_product_repository),
):
    """Get product by ID."""
    product = await repository.get(ULID(product_id))
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return ProductResponseDTO.from_entity(product)
```

## Step 6: Register Dependencies

```python
# src/infrastructure/di/app_container.py

def register_products(container: Container) -> None:
    """Register product dependencies."""
    container.register(
        IProductRepository,
        ProductRepository,
        scope=Scope.SCOPED,
    )
```

## Step 7: Add Tests

```python
# tests/unit/domain/products/test_product.py
class TestProduct:
    def test_update_price_valid(self):
        product = Product(name="Test", price=Decimal("100"))
        
        product.update_price(Decimal("150"))
        
        assert product.price == Decimal("150")
    
    def test_update_price_negative_raises(self):
        product = Product(name="Test", price=Decimal("100"))
        
        with pytest.raises(ValidationError):
            product.update_price(Decimal("-10"))
```

## Checklist

- [ ] Domain entities defined
- [ ] Value objects created
- [ ] Domain events defined
- [ ] Repository interface created
- [ ] DTOs defined
- [ ] Commands/Queries implemented
- [ ] Repository implementation created
- [ ] Router created
- [ ] Dependencies registered
- [ ] Unit tests written
- [ ] Integration tests written

## Related Documentation

- [Domain Layer](../layers/domain/index.md)
- [Application Layer](../layers/application/index.md)
- [Testing Guide](testing-guide.md)
