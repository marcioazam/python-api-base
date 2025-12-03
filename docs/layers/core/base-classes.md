# Base Classes

## Overview

The `src/core/base/` directory contains abstract base classes that provide foundational patterns for the entire application.

## Directory Structure

```
src/core/base/
├── cqrs/           # CQRS base classes
├── domain/         # Domain base classes
├── events/         # Event base classes
├── patterns/       # Design pattern implementations
├── repository/     # Repository base classes
└── __init__.py
```

## CQRS Base Classes

### Command Base

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

TResult = TypeVar("TResult")
TError = TypeVar("TError")

class Command(ABC, Generic[TResult, TError]):
    """Base class for commands."""
    
    @abstractmethod
    async def execute(self) -> Result[TResult, TError]:
        """Execute the command."""
        ...
```

### Query Base

```python
class Query(ABC, Generic[TResult]):
    """Base class for queries."""
    
    cacheable: bool = False
    cache_ttl: int = 300
    
    @abstractmethod
    async def execute(self) -> TResult:
        """Execute the query."""
        ...
```

## Domain Base Classes

### Entity Base

```python
class Entity(ABC, Generic[TId]):
    """Base class for domain entities."""
    
    id: TId
    created_at: datetime
    updated_at: datetime | None
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id)
```

### Aggregate Root

```python
class AggregateRoot(Entity[TId], Generic[TId]):
    """Base class for aggregate roots."""
    
    _domain_events: list[DomainEvent] = []
    
    def add_domain_event(self, event: DomainEvent) -> None:
        """Add a domain event to be published."""
        self._domain_events.append(event)
    
    def clear_domain_events(self) -> list[DomainEvent]:
        """Clear and return all domain events."""
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events
```

### Value Object

```python
class ValueObject(ABC):
    """Base class for value objects."""
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__
    
    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))
```

## Event Base Classes

### Domain Event

```python
@dataclass
class DomainEvent:
    """Base class for domain events."""
    
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: str | None = None
    aggregate_type: str | None = None
```

### Event Handler

```python
class EventHandler(ABC, Generic[TEvent]):
    """Base class for event handlers."""
    
    @abstractmethod
    async def handle(self, event: TEvent) -> None:
        """Handle the event."""
        ...
```

## Pattern Base Classes

### Specification

```python
class Specification(ABC, Generic[T]):
    """Base class for specifications."""
    
    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies the specification."""
        ...
    
    def and_spec(self, other: "Specification[T]") -> "Specification[T]":
        """Combine with AND."""
        return AndSpecification(self, other)
    
    def or_spec(self, other: "Specification[T]") -> "Specification[T]":
        """Combine with OR."""
        return OrSpecification(self, other)
    
    def not_spec(self) -> "Specification[T]":
        """Negate specification."""
        return NotSpecification(self)
```

## Repository Base Classes

### Repository Protocol

```python
class IRepository(Protocol, Generic[TEntity, TId]):
    """Repository interface."""
    
    async def get(self, id: TId) -> TEntity | None: ...
    async def get_all(self) -> list[TEntity]: ...
    async def add(self, entity: TEntity) -> TEntity: ...
    async def update(self, entity: TEntity) -> TEntity: ...
    async def delete(self, id: TId) -> bool: ...
    async def exists(self, id: TId) -> bool: ...
```

## Extension Points

### Creating Custom Entities

```python
from core.base.domain import Entity
from core.types import ULID

class Product(Entity[ULID]):
    name: str
    price: Decimal
    
    def apply_discount(self, percentage: Decimal) -> None:
        self.price = self.price * (1 - percentage / 100)
```

### Creating Custom Commands

```python
from core.base.cqrs import Command
from core.types.result_types import Result

@dataclass
class CreateProductCommand(Command[Product, str]):
    name: str
    price: Decimal
    
    async def execute(self) -> Result[Product, str]:
        # Implementation
        return Ok(product)
```

## Related Documentation

- [Configuration](configuration.md)
- [Protocols](protocols.md)
- [Domain Layer](../domain/index.md)
