# Cache Infrastructure

## Overview

O sistema suporta múltiplos providers de cache (Redis, Memory) através de uma interface comum.

## Cache Protocol

```python
class CacheProvider[T](Protocol):
    async def get(self, key: str) -> T | None: ...
    async def set(self, key: str, value: T, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> bool: ...
    async def exists(self, key: str) -> bool: ...
    async def clear_pattern(self, pattern: str) -> int: ...
    async def get_stats(self) -> CacheStats: ...
```

## Redis Provider

```python
class RedisCacheProvider[T](CacheProvider[T]):
    def __init__(self, client: Redis, serializer: Serializer[T] | None = None):
        self._client = client
        self._serializer = serializer or JsonSerializer()
    
    async def get(self, key: str) -> T | None:
        data = await self._client.get(key)
        if data is None:
            return None
        return self._serializer.deserialize(data)
    
    async def set(self, key: str, value: T, ttl: int | None = None) -> None:
        data = self._serializer.serialize(value)
        await self._client.set(key, data, ex=ttl)
    
    async def delete(self, key: str) -> bool:
        return await self._client.delete(key) > 0
    
    async def clear_pattern(self, pattern: str) -> int:
        keys = []
        async for key in self._client.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            return await self._client.delete(*keys)
        return 0
```

## Memory Provider (Testing)

```python
class MemoryCacheProvider[T](CacheProvider[T]):
    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._max_size = max_size
    
    async def get(self, key: str) -> T | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if entry.is_expired:
            del self._cache[key]
            return None
        return entry.value
    
    async def set(self, key: str, value: T, ttl: int | None = None) -> None:
        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)  # LRU eviction
        
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl) if ttl else None
        self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
```

## @cached Decorator

```python
def cached(
    ttl: int = 300,
    key_builder: Callable[..., str] | None = None,
    cache_provider: CacheProvider | None = None,
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            provider = cache_provider or get_default_cache()
            
            # Build cache key
            if key_builder:
                key = key_builder(*args, **kwargs)
            else:
                key = f"{func.__module__}.{func.__name__}:{hash((args, tuple(kwargs.items())))}"
            
            # Check cache
            cached_value = await provider.get(key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await provider.set(key, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator

# Usage
@cached(ttl=300, key_builder=lambda user_id: f"user:{user_id}")
async def get_user(user_id: str) -> UserDTO:
    return await repository.get(user_id)
```

## Cache Invalidation

```python
class CacheInvalidator:
    def __init__(self, cache: CacheProvider):
        self._cache = cache
    
    async def invalidate_user(self, user_id: str) -> None:
        await self._cache.delete(f"user:{user_id}")
        await self._cache.clear_pattern(f"user_list:*")
    
    async def invalidate_all_users(self) -> None:
        await self._cache.clear_pattern("user:*")
        await self._cache.clear_pattern("user_list:*")
```

## Key Patterns

| Pattern | Example | Use Case |
|---------|---------|----------|
| Entity | `user:{id}` | Single entity |
| List | `user_list:{hash}` | Paginated lists |
| Session | `session:{token}` | User sessions |
| Rate Limit | `rate:{ip}:{endpoint}` | Rate limiting |

## Best Practices

1. **Use consistent key patterns** - Document and follow conventions
2. **Set appropriate TTLs** - Balance freshness vs performance
3. **Invalidate on writes** - Keep cache consistent
4. **Use cache-aside pattern** - Check cache, then database
5. **Monitor hit rates** - Track cache effectiveness
