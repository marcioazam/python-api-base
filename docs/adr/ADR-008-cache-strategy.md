# ADR-008: Cache Strategy

## Status
Accepted

## Context

The system needs caching that:
- Reduces database load for frequently accessed data
- Supports multiple cache backends
- Provides consistent API across providers
- Enables cache invalidation patterns

## Decision

We implement a multi-provider cache strategy with protocol-based abstraction:

### Cache Provider Protocol

```python
# src/infrastructure/cache/protocols.py
class CacheProvider[T](Protocol):
    """Generic cache provider protocol."""

    async def get(self, key: str) -> T | None:
        """Get value from cache."""
        ...

    async def set(
        self,
        key: str,
        value: T,
        ttl: int | None = None,
    ) -> None:
        """Set value in cache with optional TTL."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern."""
        ...

    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        ...
```

### Providers

**Redis Provider (Production):**
```python
# src/infrastructure/cache/redis_provider.py
class RedisCacheProvider[T](CacheProvider[T]):
    def __init__(
        self,
        client: RedisClient,
        serializer: Serializer[T],
        prefix: str = "",
    ):
        ...
```

**Memory Provider (Development/Testing):**
```python
# src/infrastructure/cache/memory_provider.py
class MemoryCacheProvider[T](CacheProvider[T]):
    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
```

### Cache Decorator

```python
# src/infrastructure/cache/decorators.py
@cached(ttl=300, key_builder=lambda user_id: f"user:{user_id}")
async def get_user(user_id: str) -> UserDTO:
    ...
```

### TTL Policies

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| User profile | 5 min | Moderate change frequency |
| Configuration | 1 hour | Rarely changes |
| Session data | 30 min | Security consideration |
| Search results | 1 min | Freshness important |

### Invalidation Strategies

1. **Time-based (TTL)**: Automatic expiration
2. **Event-based**: Invalidate on write operations
3. **Pattern-based**: Clear related keys (e.g., `user:*`)

## Consequences

### Positive
- Reduced database load
- Consistent API across providers
- Easy to switch providers
- Transparent caching with decorator

### Negative
- Cache invalidation complexity
- Potential stale data
- Additional infrastructure (Redis)

### Neutral
- Memory provider useful for testing
- Requires monitoring cache hit rates

## Alternatives Considered

1. **Database query cache only** - Rejected as limited control
2. **CDN caching** - Rejected as not suitable for dynamic data
3. **Application-level memoization** - Rejected as not distributed

## References

- [src/infrastructure/cache/protocols.py](../../src/infrastructure/cache/protocols.py)
- [src/infrastructure/cache/redis_provider.py](../../src/infrastructure/cache/redis_provider.py)
- [src/infrastructure/cache/memory_provider.py](../../src/infrastructure/cache/memory_provider.py)
- [src/infrastructure/cache/decorators.py](../../src/infrastructure/cache/decorators.py)

## History

| Date | Status | Notes |
|------|--------|-------|
| 2024-12-02 | Proposed | Initial proposal |
| 2024-12-02 | Accepted | Approved for implementation |
