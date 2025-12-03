# Entities

## Overview

Entities são objetos com identidade única que persistem ao longo do tempo. Duas entidades são iguais se têm o mesmo ID, independente de seus outros atributos.

## Entity Definition

```python
from dataclasses import dataclass, field
from datetime import datetime
from ulid import ULID

@dataclass
class User:
    """User entity with identity."""
    
    id: str = field(default_factory=lambda: str(ULID()))
    email: str
    name: str
    password_hash: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
    
    def activate(self) -> None:
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def soft_delete(self) -> None:
        self.deleted_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
```

## Entity Protocols

```python
from typing import Protocol
from datetime import datetime

class Entity(Protocol):
    """Base entity with identity."""
    id: str

class TrackedEntity(Entity, Protocol):
    """Entity with timestamps."""
    created_at: datetime
    updated_at: datetime | None

class VersionedEntity(TrackedEntity, Protocol):
    """Entity with optimistic locking."""
    version: int

class SoftDeletableEntity(TrackedEntity, Protocol):
    """Entity with soft delete."""
    deleted_at: datetime | None
    
    @property
    def is_deleted(self) -> bool: ...
```

## Entity with SQLModel

```python
from sqlmodel import SQLModel, Field
from datetime import datetime
from ulid import ULID

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: str = Field(
        default_factory=lambda: str(ULID()),
        primary_key=True,
    )
    email: str = Field(unique=True, index=True)
    name: str = Field(max_length=100)
    password_hash: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(default=None)
```

## Entity Equality

```python
@dataclass
class User:
    id: str
    email: str
    name: str
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            return NotImplemented
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id)
```

## Aggregate Root

```python
@dataclass
class Order:
    """Order aggregate root."""
    
    id: str
    customer_id: str
    items: list[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_item(self, product_id: str, quantity: int, price: Decimal) -> None:
        """Add item to order (business rule enforcement)."""
        if self.status != OrderStatus.PENDING:
            raise DomainError("Cannot modify confirmed order")
        
        item = OrderItem(
            order_id=self.id,
            product_id=product_id,
            quantity=quantity,
            unit_price=price,
        )
        self.items.append(item)
    
    def confirm(self) -> None:
        """Confirm order (business rule enforcement)."""
        if not self.items:
            raise DomainError("Cannot confirm empty order")
        self.status = OrderStatus.CONFIRMED
    
    @property
    def total(self) -> Decimal:
        return sum(item.subtotal for item in self.items)
```

## Best Practices

1. **Use ULID for IDs** - Sortable, URL-safe, unique
2. **Encapsulate business logic** - Methods on entities
3. **Validate invariants** - In constructors and methods
4. **Keep entities pure** - No infrastructure dependencies
5. **Use value objects** - For complex attributes
