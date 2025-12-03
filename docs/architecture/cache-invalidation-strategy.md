# Cache Invalidation Strategy - Event-Driven

**Feature:** application-layer-improvements-2025
**Status:** Implemented
**Date:** 2025-01-02

## Overview

Event-driven cache invalidation strategy ensures query cache consistency with domain state changes by automatically invalidating cached query results when domain events are published.

## Problem Statement

Query caching improves read performance but can serve stale data if the cache is not properly invalidated when entities are modified. TTL-based expiration alone is insufficient for maintaining consistency.

## Solution

Implement event-driven cache invalidation that listens to domain events and automatically clears related cache entries using pattern matching.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Event-Driven Cache Invalidation Flow                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Command Execution                                       │
│     └─> CreateUserCommand → Handler → UserAggregate        │
│                                                             │
│  2. Domain Event Emission                                   │
│     └─> UserRegisteredEvent published to EventBus          │
│                                                             │
│  3. Cache Invalidation Handler                              │
│     └─> UserCacheInvalidationStrategy.on_user_registered() │
│         └─> cache.clear_pattern("query_cache:ListUsers:*") │
│                                                             │
│  4. Next Query Refresh                                      │
│     └─> GetUserQuery → Cache MISS → Fresh data from DB     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. CacheInvalidationStrategy (Base Class)

```python
from application.common.middleware.cache_invalidation import CacheInvalidationStrategy, InvalidationRule

class UserCacheInvalidationStrategy(CacheInvalidationStrategy):
    def __init__(self, cache: QueryCache):
        super().__init__(cache)

        # Define invalidation rules
        self.add_rule(InvalidationRule(
            event_type=UserRegisteredEvent,
            patterns=[
                "query_cache:ListUsersQuery:*",
                "query_cache:GetActiveUsersQuery:*"
            ],
            log_invalidation=True
        ))
```

### 2. Pattern Matching

Supports wildcard patterns for flexible cache key matching:

```python
# Clear all user queries
await cache.clear_pattern("query_cache:*User*:*")

# Clear specific user
await cache.clear_pattern("query_cache:GetUserQuery:*user-123*")

# Clear all list queries
await cache.clear_pattern("query_cache:List*:*")
```

### 3. Event Subscription

Connect invalidation strategy to event bus:

```python
from application.common.cqrs.event_bus import EventBus
from domain.users.events import UserRegisteredEvent, UserEmailChangedEvent

event_bus = EventBus()
strategy = UserCacheInvalidationStrategy(cache)

# Subscribe to events
event_bus.subscribe(UserRegisteredEvent, strategy.on_user_registered)
event_bus.subscribe(UserEmailChangedEvent, strategy.on_user_updated)
```

---

## Implementation Examples

### Example 1: Basic Setup

```python
from application.common.middleware.query_cache import InMemoryQueryCache
from application.common.middleware.cache_invalidation import UserCacheInvalidationStrategy
from application.common.cqrs.event_bus import EventBus

# Initialize cache
cache = InMemoryQueryCache()

# Create invalidation strategy
strategy = UserCacheInvalidationStrategy(cache)

# Setup event bus
event_bus = EventBus()

# Register handlers for domain events
from domain.users.events import (
    UserRegisteredEvent,
    UserEmailChangedEvent,
    UserDeletedEvent
)

event_bus.subscribe(UserRegisteredEvent, strategy.on_user_registered)
event_bus.subscribe(UserEmailChangedEvent, strategy.on_user_updated)
event_bus.subscribe(UserDeletedEvent, strategy.on_user_deleted)
```

### Example 2: Custom Invalidation Rules

```python
from application.common.middleware.cache_invalidation import (
    CacheInvalidationStrategy,
    InvalidationRule
)

class OrderCacheInvalidationStrategy(CacheInvalidationStrategy):
    def __init__(self, cache: QueryCache):
        super().__init__(cache)

        # Order created - invalidate customer order lists
        self.add_rule(InvalidationRule(
            event_type=OrderCreatedEvent,
            patterns=[
                "query_cache:ListOrdersQuery:*",
                "query_cache:GetCustomerOrdersQuery:*"
            ]
        ))

        # Order status changed - invalidate specific order + lists
        self.add_rule(InvalidationRule(
            event_type=OrderStatusChangedEvent,
            patterns=[
                "query_cache:GetOrderQuery:*",
                "query_cache:ListOrdersQuery:*",
                "query_cache:GetPendingOrdersQuery:*"
            ]
        ))

    async def on_order_created(self, event: OrderCreatedEvent):
        await self.invalidate(event)

    async def on_order_status_changed(self, event: OrderStatusChangedEvent):
        await self.invalidate(event)
```

### Example 3: Composite Strategy (Multiple Domains)

```python
from application.common.middleware.cache_invalidation import CompositeCacheInvalidationStrategy

# Create composite strategy
composite = CompositeCacheInvalidationStrategy(cache)

# Add strategies for different domains
composite.add_strategy(UserCacheInvalidationStrategy(cache))
composite.add_strategy(OrderCacheInvalidationStrategy(cache))
composite.add_strategy(ProductCacheInvalidationStrategy(cache))

# Single subscription handles all events
event_bus.subscribe_all(composite.on_event)  # Handles all domain events
```

### Example 4: Command-Based Invalidation (Alternative)

Instead of event-based, invalidate immediately after command:

```python
from application.common.middleware.cache_invalidation import CacheInvalidationMiddleware

# Map commands to cache patterns
invalidation_map = {
    CreateUserCommand: ["query_cache:ListUsersQuery:*"],
    UpdateUserCommand: ["query_cache:GetUserQuery:*", "query_cache:ListUsersQuery:*"],
    DeleteUserCommand: ["query_cache:GetUserQuery:*", "query_cache:ListUsersQuery:*"]
}

# Add middleware to command bus
cache_invalidation_mw = CacheInvalidationMiddleware(cache, invalidation_map)
command_bus.add_middleware(cache_invalidation_mw)
```

---

## Configuration

### Query Cache with Invalidation

```python
from application.common.middleware import (
    QueryCacheMiddleware,
    QueryCacheConfig,
    InMemoryQueryCache,
    UserCacheInvalidationStrategy
)

# Cache configuration
cache_config = QueryCacheConfig(
    ttl_seconds=300,  # 5 minutes
    key_prefix="query_cache",
    enabled=True,
    cache_all_queries=False,  # Explicit opt-in via get_cache_key()
    log_hits=True,
    log_misses=False
)

# Initialize cache
cache = InMemoryQueryCache()

# Cache middleware for queries
query_cache_mw = QueryCacheMiddleware(cache, cache_config)
query_bus.add_middleware(query_cache_mw)

# Invalidation strategy for events
invalidation_strategy = UserCacheInvalidationStrategy(cache)
event_bus.subscribe(UserRegisteredEvent, invalidation_strategy.on_user_registered)
```

---

## Pattern Guidelines

### Cache Key Patterns

Use consistent key patterns for predictable invalidation:

```python
# Query cache keys format
"query_cache:{QueryType}:{entity_type}:{entity_id}"
"query_cache:{QueryType}:{hash}"

# Examples
"query_cache:GetUserQuery:user:123"
"query_cache:ListUsersQuery:active:hash_abc123"
"query_cache:GetOrdersByCustomerQuery:customer:456"
```

### Invalidation Pattern Strategies

1. **Specific Entity Invalidation**
   ```python
   # Invalidate specific user
   f"query_cache:GetUserQuery:*{user_id}*"
   ```

2. **Query Type Invalidation**
   ```python
   # Invalidate all ListUsers queries
   "query_cache:ListUsersQuery:*"
   ```

3. **Broad Invalidation**
   ```python
   # Invalidate all user-related queries
   "query_cache:*User*:*"
   ```

4. **Selective Invalidation**
   ```python
   # Only active user lists
   "query_cache:GetActiveUsersQuery:*"
   ```

---

## Performance Considerations

### Pattern Matching Performance

- In-memory cache uses `fnmatch` for pattern matching: O(n) where n = number of cache entries
- For production with Redis, use `SCAN` + pattern matching instead of `KEYS`
- Consider cache size limits to prevent unbounded growth

### Invalidation Overhead

```python
# Measure invalidation impact
import time

start = time.perf_counter()
cleared = await cache.clear_pattern("query_cache:ListUsers:*")
duration = time.perf_counter() - start

logger.info(f"Cleared {cleared} entries in {duration*1000:.2f}ms")
```

Typical metrics:
- In-memory: <1ms for 1000 entries
- Redis: 5-10ms for 10,000 entries (SCAN)

### Event Handler Async

Invalidation handlers are async and don't block command execution:

```python
# Event publishing is fire-and-forget
await event_bus.publish(UserRegisteredEvent(...))
# ^ Returns immediately, invalidation happens async
```

---

## Testing

### Unit Tests

```python
import pytest
from application.common.middleware.cache_invalidation import UserCacheInvalidationStrategy
from domain.users.events import UserRegisteredEvent

@pytest.mark.asyncio
async def test_user_registered_invalidates_list_queries():
    # Arrange
    cache = InMemoryQueryCache()

    # Populate cache
    await cache.set("query_cache:ListUsersQuery:active", [{"id": "1"}], ttl=300)
    assert await cache.get("query_cache:ListUsersQuery:active") is not None

    # Act
    strategy = UserCacheInvalidationStrategy(cache)
    event = UserRegisteredEvent(user_id="new-user", email="test@example.com")
    await strategy.on_user_registered(event)

    # Assert
    cached = await cache.get("query_cache:ListUsersQuery:active")
    assert cached is None  # Cache cleared
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_cache_invalidation_end_to_end():
    # Setup
    cache = InMemoryQueryCache()
    query_bus = QueryBus()
    command_bus = CommandBus()
    event_bus = EventBus()

    # Add cache middleware
    query_bus.add_middleware(QueryCacheMiddleware(cache))

    # Add invalidation strategy
    strategy = UserCacheInvalidationStrategy(cache)
    event_bus.subscribe(UserRegisteredEvent, strategy.on_user_registered)

    # Execute query (cache miss)
    users1 = await query_bus.dispatch(ListUsersQuery())
    assert users1 == []

    # Execute again (cache hit)
    users2 = await query_bus.dispatch(ListUsersQuery())
    assert users2 == []  # From cache

    # Execute command (triggers event)
    await command_bus.dispatch(CreateUserCommand(email="test@example.com"))

    # Query again (cache invalidated, fresh data)
    users3 = await query_bus.dispatch(ListUsersQuery())
    assert len(users3) == 1  # Fresh from DB
```

---

## Production Considerations

### Redis Cache Implementation

```python
from redis.asyncio import Redis
import fnmatch

class RedisCacheInvalidation:
    def __init__(self, redis: Redis):
        self._redis = redis

    async def clear_pattern(self, pattern: str) -> int:
        """Clear Redis keys matching pattern."""
        cursor = 0
        cleared = 0

        # Use SCAN for safe iteration
        while True:
            cursor, keys = await self._redis.scan(
                cursor,
                match=pattern,
                count=100
            )

            if keys:
                await self._redis.delete(*keys)
                cleared += len(keys)

            if cursor == 0:
                break

        return cleared
```

### Distributed Cache Considerations

- **Cache Stampede**: Prevent thundering herd with locking
- **Consistency**: Ensure event ordering
- **Failure Handling**: Retry failed invalidations
- **Monitoring**: Track invalidation metrics

---

## Monitoring & Observability

### Metrics

```python
# Track cache invalidation metrics
metrics = {
    "cache_invalidations_total": Counter("cache_invalidations", ["event_type", "pattern"]),
    "cache_keys_cleared": Histogram("cache_keys_cleared", ["pattern"]),
    "cache_invalidation_duration": Histogram("cache_invalidation_ms", ["pattern"])
}

# In strategy
async def invalidate(self, event):
    start = time.perf_counter()
    cleared = await self._cache.clear_pattern(pattern)
    duration = time.perf_counter() - start

    metrics["cache_invalidations_total"].labels(
        event_type=type(event).__name__,
        pattern=pattern
    ).inc()

    metrics["cache_keys_cleared"].labels(pattern=pattern).observe(cleared)
    metrics["cache_invalidation_duration"].labels(pattern=pattern).observe(duration * 1000)
```

### Logging

Structured logging is enabled by default:

```json
{
  "event": "cache_invalidated",
  "event_type": "UserRegisteredEvent",
  "pattern": "query_cache:ListUsersQuery:*",
  "keys_cleared": 5,
  "operation": "CACHE_INVALIDATION",
  "timestamp": "2025-01-02T10:30:00Z"
}
```

---

## Decision Record

### ADR-001: Event-Based vs Command-Based Invalidation

**Decision:** Implement event-based cache invalidation as primary strategy.

**Rationale:**
- Events represent domain changes at the right level of abstraction
- Decouples cache invalidation from command handlers
- Supports multiple subscribers (cache, notifications, etc.)
- Aligns with CQRS and event sourcing patterns

**Trade-offs:**
- ✅ Pro: Loose coupling, extensible
- ✅ Pro: Consistent with domain event architecture
- ⚠️ Con: Async - small delay between command and invalidation
- ⚠️ Con: Requires event bus infrastructure

**Alternative:** Command-based middleware invalidation (also provided as option).

---

## References

- `src/application/common/middleware/cache_invalidation.py` - Implementation
- `src/application/common/middleware/query_cache.py` - Query cache middleware
- `docs/architecture/cqrs-implementation.md` - CQRS architecture
- `docs/architecture/event-bus.md` - Event bus documentation

---

**Status:** ✅ Implemented
**Version:** 1.0
**Last Updated:** 2025-01-02
