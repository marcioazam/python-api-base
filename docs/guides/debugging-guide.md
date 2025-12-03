# Debugging Guide

## Overview

Guia para debugging de problemas comuns no Python API Base.

## Common Issues

### 1. Import Errors

**Symptom:**
```
ModuleNotFoundError: No module named 'core'
```

**Solution:**
```bash
# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"

# Or install in editable mode
pip install -e .
```

### 2. Database Connection

**Symptom:**
```
sqlalchemy.exc.OperationalError: connection refused
```

**Solution:**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Start if needed
docker compose -f deployments/docker/docker-compose.dev.yml up -d postgres

# Verify connection
psql -h localhost -U postgres -d mydb
```

### 3. Redis Connection

**Symptom:**
```
redis.exceptions.ConnectionError: Connection refused
```

**Solution:**
```bash
# Check if Redis is running
docker ps | grep redis

# Start if needed
docker compose up -d redis

# Test connection
redis-cli ping
```

### 4. JWT Errors

**Symptom:**
```
jwt.exceptions.InvalidSignatureError
```

**Solution:**
```bash
# Check secret key is set
echo $SECURITY__SECRET_KEY

# Generate new key if needed
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Debugging Tools

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

# Add context
logger.info("processing_request", user_id=user_id, action="create")

# Log errors with traceback
logger.exception("operation_failed", error=str(e))
```

### Request Tracing

```python
# Check correlation ID in logs
grep "correlation_id=abc123" logs/app.log

# Or use structured query
jq 'select(.correlation_id == "abc123")' logs/app.json
```

### Database Queries

```python
# Enable SQL echo
DATABASE__ECHO=true

# Or in code
engine = create_async_engine(url, echo=True)
```

### Profiling

```python
import cProfile
import pstats

# Profile a function
profiler = cProfile.Profile()
profiler.enable()
# ... code to profile ...
profiler.disable()

stats = pstats.Stats(profiler)
stats.sort_stats("cumulative")
stats.print_stats(10)
```

## Debug Endpoints

```python
# Add debug router (development only)
@router.get("/debug/config")
async def debug_config():
    if not settings.debug:
        raise HTTPException(403)
    return {
        "database_url": settings.database.url.split("@")[1],  # Hide credentials
        "redis_enabled": settings.redis.enabled,
        "log_level": settings.observability.log_level,
    }

@router.get("/debug/health")
async def debug_health():
    return {
        "database": await check_database(),
        "redis": await check_redis(),
        "kafka": await check_kafka(),
    }
```

## Log Analysis

```bash
# View recent errors
grep -i error logs/app.log | tail -20

# Count errors by type
jq -r '.error_type' logs/app.json | sort | uniq -c | sort -rn

# Find slow requests
jq 'select(.duration_ms > 1000)' logs/app.json

# Filter by user
jq 'select(.user_id == "user-123")' logs/app.json
```

## Memory Issues

```python
# Check memory usage
import tracemalloc

tracemalloc.start()
# ... code ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics("lineno")

for stat in top_stats[:10]:
    print(stat)
```

## Performance Issues

```bash
# Profile with py-spy
py-spy record -o profile.svg -- python -m uvicorn src.main:app

# Analyze with flamegraph
open profile.svg
```

## Testing Debug

```bash
# Run single test with output
pytest tests/unit/test_user.py -v -s

# Run with debugger
pytest tests/unit/test_user.py --pdb

# Show local variables on failure
pytest tests/unit/test_user.py -l
```

## Best Practices

1. **Use structured logging** - JSON format for parsing
2. **Add correlation IDs** - Track requests across services
3. **Enable debug mode locally** - But never in production
4. **Use profiling** - For performance issues
5. **Check logs first** - Before debugging code
