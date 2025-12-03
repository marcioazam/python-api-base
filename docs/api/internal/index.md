# Internal API Documentation

## Overview

Internal APIs define contracts for service-to-service communication within the application.

## Service Interfaces

### User Service

```python
class IUserService(Protocol):
    async def get_user(self, user_id: str) -> User | None: ...
    async def create_user(self, data: CreateUserDTO) -> User: ...
    async def update_user(self, user_id: str, data: UpdateUserDTO) -> User: ...
    async def delete_user(self, user_id: str) -> bool: ...
    async def authenticate(self, email: str, password: str) -> TokenPair | None: ...
```

### Item Service

```python
class IItemService(Protocol):
    async def get_item(self, item_id: str) -> Item | None: ...
    async def get_items_by_owner(self, owner_id: str) -> list[Item]: ...
    async def create_item(self, data: CreateItemDTO) -> Item: ...
    async def update_item(self, item_id: str, data: UpdateItemDTO) -> Item: ...
    async def delete_item(self, item_id: str) -> bool: ...
```

## Event Contracts

### Domain Events

| Event | Payload | Description |
|-------|---------|-------------|
| `UserCreated` | `{user_id, email}` | New user created |
| `UserActivated` | `{user_id}` | User activated |
| `ItemCreated` | `{item_id, owner_id}` | New item created |
| `ItemPriceChanged` | `{item_id, old_price, new_price}` | Item price updated |

### Event Schema

```python
@dataclass
class DomainEvent:
    event_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    occurred_at: datetime
    data: dict
```

## Cache Contracts

### Key Patterns

| Pattern | Example | TTL |
|---------|---------|-----|
| `user:{id}` | `user:123` | 5 min |
| `user:{id}:items` | `user:123:items` | 2 min |
| `item:{id}` | `item:456` | 5 min |
| `search:{hash}` | `search:abc123` | 1 min |

### Invalidation

| Event | Keys Invalidated |
|-------|------------------|
| User updated | `user:{id}`, `user:{id}:*` |
| Item created | `user:{owner_id}:items` |
| Item updated | `item:{id}` |

## Message Queue Contracts

### Topics

| Topic | Message Type | Consumer |
|-------|--------------|----------|
| `user.events` | Domain events | Analytics |
| `item.events` | Domain events | Search indexer |
| `notifications` | Notification requests | Notification service |

### Message Schema

```json
{
  "id": "msg-123",
  "type": "UserCreated",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": {
    "user_id": "123",
    "email": "user@example.com"
  }
}
```

## Related

- [Domain Events](../../layers/domain/events.md)
- [Cache](../../layers/infrastructure/cache.md)
