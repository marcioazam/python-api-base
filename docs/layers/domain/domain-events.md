# Domain Events

## Overview

Domain Events representam mudanças significativas no domínio que outros componentes podem reagir. São imutáveis e contêm todas as informações necessárias sobre o evento.

## Event Base Class

```python
from dataclasses import dataclass, field
from datetime import datetime
from ulid import ULID

@dataclass(frozen=True)
class DomainEvent:
    """Base class for domain events."""
    
    event_id: str = field(default_factory=lambda: str(ULID()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def event_type(self) -> str:
        return self.__class__.__name__
```

## User Events

```python
@dataclass(frozen=True)
class UserCreated(DomainEvent):
    """Event raised when a user is created."""
    
    user_id: str
    email: str
    name: str

@dataclass(frozen=True)
class UserUpdated(DomainEvent):
    """Event raised when a user is updated."""
    
    user_id: str
    changes: dict[str, tuple[Any, Any]]  # field: (old, new)

@dataclass(frozen=True)
class UserDeleted(DomainEvent):
    """Event raised when a user is deleted."""
    
    user_id: str
    deleted_by: str | None = None

@dataclass(frozen=True)
class UserActivated(DomainEvent):
    """Event raised when a user is activated."""
    
    user_id: str

@dataclass(frozen=True)
class UserDeactivated(DomainEvent):
    """Event raised when a user is deactivated."""
    
    user_id: str
    reason: str | None = None
```

## Order Events

```python
@dataclass(frozen=True)
class OrderCreated(DomainEvent):
    """Event raised when an order is created."""
    
    order_id: str
    customer_id: str
    items: tuple[dict, ...]
    total: Decimal

@dataclass(frozen=True)
class OrderConfirmed(DomainEvent):
    """Event raised when an order is confirmed."""
    
    order_id: str
    confirmed_at: datetime

@dataclass(frozen=True)
class OrderCancelled(DomainEvent):
    """Event raised when an order is cancelled."""
    
    order_id: str
    reason: str
    cancelled_by: str
```

## Event Publisher Protocol

```python
from typing import Protocol

class EventPublisher(Protocol):
    """Protocol for publishing domain events."""
    
    async def publish(self, event: DomainEvent) -> None:
        """Publish a single event."""
        ...
    
    async def publish_all(self, events: list[DomainEvent]) -> None:
        """Publish multiple events."""
        ...
```

## Event Handler Protocol

```python
class EventHandler(Protocol[T]):
    """Protocol for handling domain events."""
    
    async def handle(self, event: T) -> None:
        """Handle the event."""
        ...
```

## Entity with Events

```python
@dataclass
class User:
    id: str
    email: str
    name: str
    is_active: bool = True
    _events: list[DomainEvent] = field(default_factory=list, repr=False)
    
    @classmethod
    def create(cls, email: str, name: str) -> "User":
        user = cls(
            id=str(ULID()),
            email=email,
            name=name,
        )
        user._events.append(UserCreated(
            user_id=user.id,
            email=email,
            name=name,
        ))
        return user
    
    def activate(self) -> None:
        if not self.is_active:
            self.is_active = True
            self._events.append(UserActivated(user_id=self.id))
    
    def deactivate(self, reason: str | None = None) -> None:
        if self.is_active:
            self.is_active = False
            self._events.append(UserDeactivated(
                user_id=self.id,
                reason=reason,
            ))
    
    def collect_events(self) -> list[DomainEvent]:
        """Collect and clear pending events."""
        events = self._events.copy()
        self._events.clear()
        return events
```

## Event Handlers

```python
class SendWelcomeEmailHandler(EventHandler[UserCreated]):
    def __init__(self, email_service: EmailService):
        self._email_service = email_service
    
    async def handle(self, event: UserCreated) -> None:
        await self._email_service.send_welcome(
            to=event.email,
            name=event.name,
        )

class UpdateSearchIndexHandler(EventHandler[UserCreated]):
    def __init__(self, search_service: SearchService):
        self._search_service = search_service
    
    async def handle(self, event: UserCreated) -> None:
        await self._search_service.index_user(
            user_id=event.user_id,
            email=event.email,
            name=event.name,
        )
```

## Event Dispatcher

```python
class EventDispatcher:
    def __init__(self):
        self._handlers: dict[type, list[EventHandler]] = {}
    
    def register(self, event_type: type, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    async def dispatch(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            await handler.handle(event)
    
    async def dispatch_all(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.dispatch(event)
```

## Usage in Use Case

```python
class CreateUserUseCase:
    def __init__(
        self,
        repository: IUserRepository,
        event_dispatcher: EventDispatcher,
    ):
        self._repository = repository
        self._dispatcher = event_dispatcher
    
    async def execute(self, email: str, name: str) -> User:
        user = User.create(email=email, name=name)
        created = await self._repository.create(user)
        
        # Dispatch collected events
        events = user.collect_events()
        await self._dispatcher.dispatch_all(events)
        
        return created
```

## Best Practices

1. **Events are immutable** - Use frozen dataclasses
2. **Events are past tense** - UserCreated, not CreateUser
3. **Include all context** - Event should be self-contained
4. **Collect, don't publish immediately** - Publish after persistence
5. **Handle failures gracefully** - Use outbox pattern for reliability
