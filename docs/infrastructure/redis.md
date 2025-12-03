# Redis Integration

## Overview

Redis é usado para cache, sessões e rate limiting.

## Configuration

```python
class RedisSettings(BaseSettings):
    url: str = "redis://localhost:6379/0"
    max_connections: int = 10
    decode_responses: bool = True
```

## Environment Variables

```bash
REDIS__URL=redis://localhost:6379/0
REDIS__MAX_CONNECTIONS=10
```

## Client Setup

```python
import redis.asyncio as redis

async def get_redis_client() -> redis.Redis:
    return redis.from_url(
        settings.redis.url,
        max_connections=settings.redis.max_connections,
        decode_responses=True,
    )
```

## Cache Strategies

### Cache-Aside

```python
async def get_user(user_id: str) -> User | None:
    # 1. Check cache
    cached = await redis.get(f"user:{user_id}")
    if cached:
        return User.model_validate_json(cached)
    
    # 2. Query database
    user = await repository.get(user_id)
    if user:
        # 3. Store in cache
        await redis.set(f"user:{user_id}", user.model_dump_json(), ex=300)
    
    return user
```

### Write-Through

```python
async def update_user(user: User) -> User:
    # 1. Update database
    updated = await repository.update(user)
    
    # 2. Update cache
    await redis.set(f"user:{user.id}", updated.model_dump_json(), ex=300)
    
    return updated
```

## Key Patterns

| Pattern | Example | Use Case |
|---------|---------|----------|
| Entity | `user:{id}` | Single entity cache |
| List | `users:list:{hash}` | Paginated lists |
| Session | `session:{token}` | User sessions |
| Rate Limit | `rate:{ip}:{endpoint}` | Rate limiting |
| Lock | `lock:{resource}` | Distributed locks |

## Rate Limiting

```python
async def check_rate_limit(key: str, limit: int, window: int) -> bool:
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window)
    return current <= limit

# Usage
if not await check_rate_limit(f"rate:{ip}:/api/users", 100, 60):
    raise RateLimitExceeded()
```

## Distributed Locks

```python
async def acquire_lock(key: str, ttl: int = 10) -> bool:
    return await redis.set(f"lock:{key}", "1", nx=True, ex=ttl)

async def release_lock(key: str) -> None:
    await redis.delete(f"lock:{key}")

# Usage
if await acquire_lock("process-order-123"):
    try:
        await process_order("123")
    finally:
        await release_lock("process-order-123")
```

## Session Storage

```python
async def create_session(user_id: str, data: dict) -> str:
    session_id = secrets.token_urlsafe(32)
    await redis.hset(f"session:{session_id}", mapping={
        "user_id": user_id,
        **data,
    })
    await redis.expire(f"session:{session_id}", 86400)  # 24h
    return session_id

async def get_session(session_id: str) -> dict | None:
    data = await redis.hgetall(f"session:{session_id}")
    return data if data else None
```

## Pub/Sub

```python
# Publisher
async def publish_event(channel: str, message: dict) -> None:
    await redis.publish(channel, json.dumps(message))

# Subscriber
async def subscribe(channel: str, handler: Callable) -> None:
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            await handler(json.loads(message["data"]))
```

## Monitoring

```bash
# Connection info
redis-cli INFO clients

# Memory usage
redis-cli INFO memory

# Key statistics
redis-cli INFO keyspace

# Monitor commands
redis-cli MONITOR
```

## Best Practices

1. **Set TTLs** - Prevent memory bloat
2. **Use key prefixes** - Organize keys logically
3. **Monitor memory** - Set maxmemory policy
4. **Use pipelines** - For multiple operations
5. **Handle failures** - Redis is not persistent by default
