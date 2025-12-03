# CQRS Middleware Configuration Guide

## Overview

This guide covers the configuration and usage of CQRS middleware in the Python API Base project. Middleware provides cross-cutting concerns like logging, metrics, caching, and resilience.

## Architecture

See [ADR-005: CQRS Bootstrap Pattern](../architecture/adr/ADR-005-cqrs-bootstrap-pattern.md) for the architectural rationale behind the middleware system.

### Middleware Layers

Middleware is applied in the following order (outer to inner):

1. **Observability Layer** (Logging + Metrics) - Tracks all operations
2. **Query Cache Layer** (QueryBus only) - Caches query results
3. **Resilience Layer** (Circuit Breaker + Retry) - Optional, for fault tolerance

```
HTTP Request
    ↓
CommandBus.dispatch(command)
    ↓
[LoggingMiddleware] ← Logs command execution
    ↓
[MetricsMiddleware] ← Tracks metrics
    ↓
[ResilienceMiddleware] ← Retry + Circuit Breaker (optional)
    ↓
Handler Factory (creates fresh session + repo)
    ↓
Handler.handle(command)
    ↓
Database Operation
```

## Available Middleware

### 1. Logging Middleware

Provides structured logging with correlation IDs for all commands and queries.

**Features:**
- Request/response logging
- Duration tracking
- Correlation ID propagation
- Structured extra fields for log aggregation

**Configuration:**

```python
from application.common.middleware import LoggingMiddleware, LoggingConfig

config = LoggingConfig(
    log_request=True,
    log_response=True,
    log_duration=True,
    include_command_data=False,  # ⚠️ Set True only for debugging (may log sensitive data)
    max_data_length=500,
)

logging_middleware = LoggingMiddleware(config)
command_bus.add_middleware(logging_middleware)
query_bus.add_middleware(logging_middleware)
```

**Environment Variables:**
```bash
CQRS_LOG_COMMAND_DATA=false  # Set to 'true' for debugging only
```

**Example Log Output:**

```json
{
  "timestamp": "2025-01-02T14:30:45.123Z",
  "level": "INFO",
  "message": "Command CreateUserCommand completed in 45.32ms",
  "extra": {
    "request_id": "a1b2c3d4",
    "command_type": "CreateUserCommand",
    "duration_ms": 45.32,
    "operation": "COMMAND_EXECUTION",
    "success": true
  }
}
```

### 2. Metrics Middleware

Collects performance metrics and detects slow operations.

**Features:**
- Command execution duration tracking
- Success/failure rate tracking
- Slow command detection (configurable threshold)
- Statistics aggregation

**Configuration:**

```python
from application.common.middleware import (
    MetricsMiddleware,
    MetricsConfig,
    InMemoryMetricsCollector,
)

metrics_collector = InMemoryMetricsCollector()
config = MetricsConfig(
    enabled=True,
    track_duration=True,
    track_success_rate=True,
    detect_slow_commands=True,
    slow_threshold_ms=1000.0,  # Commands slower than 1s are "slow"
)

metrics_middleware = MetricsMiddleware(metrics_collector, config)
command_bus.add_middleware(metrics_middleware)
query_bus.add_middleware(metrics_middleware)

# Get statistics
stats = metrics_collector.get_statistics("CreateUserCommand")
print(f"Avg duration: {stats['avg_duration_ms']}ms")
print(f"Success rate: {stats['success_rate'] * 100}%")
```

**Environment Variables:**
```bash
CQRS_SLOW_THRESHOLD_MS=1000.0  # Threshold for slow command detection
```

**Example Metrics:**

```python
{
  "command_type": "CreateUserCommand",
  "total_executions": 1250,
  "success_count": 1230,
  "failure_count": 20,
  "success_rate": 0.984,
  "avg_duration_ms": 42.5,
  "min_duration_ms": 15.2,
  "max_duration_ms": 320.5
}
```

### 3. Query Cache Middleware

Caches query results to reduce database load and improve response times.

**Features:**
- Automatic query result caching
- Configurable TTL
- Cache hit/miss logging
- Per-query opt-in or cache-all mode

**Configuration:**

```python
from application.common.middleware import (
    QueryCacheMiddleware,
    QueryCacheConfig,
    InMemoryQueryCache,
)

query_cache = InMemoryQueryCache()
config = QueryCacheConfig(
    ttl_seconds=300,  # 5 minutes
    key_prefix="query_cache",
    enabled=True,
    cache_all_queries=False,  # Only cache queries with explicit cache keys
    log_hits=True,
    log_misses=False,
)

cache_middleware = QueryCacheMiddleware(query_cache, config)
query_bus.add_middleware(cache_middleware)  # QueryBus only!
```

**Environment Variables:**
```bash
QUERY_CACHE_TTL_SECONDS=300  # Cache TTL in seconds
CACHE_ALL_QUERIES=false      # Cache all queries (default: false)
```

**Query Opt-In to Caching:**

```python
from dataclasses import dataclass
from application.common.cqrs import BaseQuery

@dataclass(frozen=True, kw_only=True)
class GetUserByIdQuery(BaseQuery):
    user_id: str

    def get_cache_key(self) -> str:
        """Opt-in to caching by providing a cache key."""
        return f"user:{self.user_id}"
```

**Example Log:**
```json
{
  "level": "INFO",
  "message": "Query cache HIT for GetUserByIdQuery",
  "extra": {
    "query_type": "GetUserByIdQuery",
    "cache_key": "user:01HJ9K7...",
    "operation": "QUERY_CACHE_HIT"
  }
}
```

### 4. Resilience Middleware (Optional)

Provides retry with exponential backoff and circuit breaker pattern.

**⚠️ Important:** Resilience is **disabled by default** per [ADR-003: Resilience Layers](../architecture/adr/ADR-003-resilience-layers.md). The HTTP layer already provides resilience. Only enable CQRS resilience for domain-specific scenarios.

**Features:**
- Exponential backoff retry
- Circuit breaker (CLOSED → OPEN → HALF_OPEN)
- Configurable retry and failure thresholds

**Configuration:**

```python
from application.common.middleware import (
    ResilienceMiddleware,
    RetryConfig,
    CircuitBreakerConfig,
)

retry_config = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=(TimeoutError, ConnectionError, OSError),
)

circuit_config = CircuitBreakerConfig(
    failure_threshold=5,  # Open circuit after 5 failures
    recovery_timeout=60.0,  # Try to recover after 60 seconds
    half_open_max_calls=1,  # Test with 1 call when half-open
)

resilience_middleware = ResilienceMiddleware(
    retry_config=retry_config,
    circuit_config=circuit_config,
)

command_bus.add_middleware(resilience_middleware)
```

**Environment Variables:**
```bash
CQRS_RETRY_MAX_RETRIES=3
CQRS_RETRY_BASE_DELAY=1.0
CQRS_RETRY_MAX_DELAY=30.0
CQRS_CIRCUIT_FAILURE_THRESHOLD=5
CQRS_CIRCUIT_RECOVERY_TIMEOUT=60.0
```

## Bootstrap Configuration

The CQRS system is bootstrapped during application startup with automatic middleware configuration.

### Default Configuration

```python
# src/main.py
from infrastructure.di.cqrs_bootstrap import bootstrap_cqrs

# In startup event
await bootstrap_cqrs(
    command_bus=container.command_bus(),
    query_bus=container.query_bus(),
    configure_middleware=True,      # Enable middleware (default)
    enable_resilience=False,        # Resilience disabled (default, per ADR-003)
    enable_query_cache=True,        # Query cache enabled (default)
)
```

### Enable Resilience

To enable CQRS resilience for specific scenarios:

```python
await bootstrap_cqrs(
    command_bus=container.command_bus(),
    query_bus=container.query_bus(),
    enable_resilience=True,  # ✅ Enable for domain-specific resilience
)
```

### Custom Middleware Configuration

For advanced use cases, manually configure middleware:

```python
from infrastructure.di.cqrs_bootstrap import configure_cqrs_middleware

configure_cqrs_middleware(
    command_bus=command_bus,
    query_bus=query_bus,
    enable_resilience=False,
    enable_observability=True,
    enable_query_cache=True,
)
```

## Testing Middleware

### Unit Testing with Middleware

```python
import pytest
from application.common.middleware import LoggingMiddleware

@pytest.mark.asyncio
async def test_middleware_logs_command_execution():
    """Test that logging middleware logs command execution."""
    logging_middleware = LoggingMiddleware()

    async def mock_handler(cmd):
        return Ok({"result": "success"})

    command = CreateUserCommand(email="test@example.com", password="Test123!")

    result = await logging_middleware(command, mock_handler)

    assert result.is_ok()
    # Verify logs (use caplog fixture)
```

### Integration Testing

```python
@pytest.fixture
async def configured_command_bus():
    """Command bus with all middleware configured."""
    bus = CommandBus()

    # Configure middleware
    configure_cqrs_middleware(
        command_bus=bus,
        query_bus=QueryBus(),
        enable_resilience=True,  # Test resilience
    )

    # Register handlers
    await register_user_handlers(bus, QueryBus())

    return bus

@pytest.mark.asyncio
async def test_command_with_full_middleware_stack(configured_command_bus):
    """Test command execution through full middleware stack."""
    command = CreateUserCommand(email="test@example.com", password="Pass123!")

    result = await configured_command_bus.dispatch(command)

    assert result.is_ok()
```

## Best Practices

### 1. Logging

✅ **DO:**
- Use structured logging with `extra` fields
- Propagate correlation IDs
- Log command type, duration, and success/failure
- Keep log messages concise

❌ **DON'T:**
- Log sensitive data (passwords, tokens) in production
- Set `include_command_data=True` in production
- Log at DEBUG level in production

### 2. Metrics

✅ **DO:**
- Track command duration and success rates
- Set appropriate slow command thresholds (1000ms default)
- Use metrics to identify performance bottlenecks
- Aggregate metrics for dashboards

❌ **DON'T:**
- Ignore slow command warnings
- Set threshold too low (< 100ms)
- Forget to monitor metrics in production

### 3. Query Caching

✅ **DO:**
- Opt-in queries explicitly with `get_cache_key()`
- Use appropriate TTL (300s default for most queries)
- Invalidate cache on mutations (commands)
- Use Redis in production for distributed caching

❌ **DON'T:**
- Enable `cache_all_queries=True` without testing
- Cache queries with user-specific data without proper key
- Use very long TTL for frequently changing data
- Forget to configure cache invalidation

### 4. Resilience

✅ **DO:**
- Only enable for domain-specific scenarios
- Configure appropriate retry limits (3-5 retries max)
- Use circuit breaker for external dependencies
- Monitor circuit breaker state transitions
- Test failure scenarios

❌ **DON'T:**
- Enable resilience globally without need (HTTP layer handles it)
- Set too many retries (exhausts resources)
- Retry non-idempotent operations without idempotency keys
- Ignore circuit breaker OPEN state

## Monitoring

### Log Aggregation

Structured logs can be aggregated using:
- **Elasticsearch**: Full-text search and analytics
- **CloudWatch**: AWS log aggregation
- **DataDog**: Metrics and log correlation

**Example Elasticsearch Query:**

```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "extra.command_type": "CreateUserCommand" } },
        { "range": { "extra.duration_ms": { "gte": 1000 } } }
      ]
    }
  }
}
```

### Metrics Dashboards

Create dashboards tracking:
- **Command Success Rate**: `success_count / total_executions`
- **P95 Duration**: 95th percentile command duration
- **Slow Commands**: Commands exceeding threshold
- **Circuit Breaker State**: OPEN/CLOSED/HALF_OPEN

## Troubleshooting

### High Command Latency

**Symptoms:** Commands taking > 1000ms

**Solutions:**
1. Check metrics for slow commands
2. Profile database queries
3. Enable query cache for read-heavy queries
4. Optimize N+1 queries

### Circuit Breaker Always Open

**Symptoms:** `CircuitBreakerOpenError` in logs

**Solutions:**
1. Check downstream service health
2. Increase `failure_threshold` if too sensitive
3. Increase `recovery_timeout` for slow services
4. Verify retryable exceptions configuration

### Cache Hit Rate Low

**Symptoms:** < 50% cache hit rate

**Solutions:**
1. Verify queries have `get_cache_key()` method
2. Check TTL is appropriate for data freshness
3. Ensure cache not being invalidated too frequently
4. Monitor cache size and eviction

## Related Documentation

- [ADR-002: DTO vs Mapper Strategy](../architecture/adr/ADR-002-dto-vs-mapper-strategy.md)
- [ADR-003: Resilience Layers](../architecture/adr/ADR-003-resilience-layers.md)
- [ADR-004: Unit of Work Strategy](../architecture/adr/ADR-004-unit-of-work-strategy.md)
- [ADR-005: CQRS Bootstrap Pattern](../architecture/adr/ADR-005-cqrs-bootstrap-pattern.md)
- [Testing Guide](testing-guide.md)
- [Integration Guide](integration-guide.md)
