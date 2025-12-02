# ADR-009: Resilience Patterns

## Status
Accepted

## Context

The system needs fault tolerance mechanisms that:
- Prevent cascade failures
- Handle transient errors gracefully
- Limit resource consumption
- Provide fallback behaviors

## Decision

We implement multiple resilience patterns:

### Circuit Breaker

```python
# src/infrastructure/resilience/patterns.py
@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5      # Failures to open
    success_threshold: int = 3      # Successes to close
    timeout: float = 30.0           # Seconds in half-open
    excluded_exceptions: tuple = () # Don't count these

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing fast
    HALF_OPEN = "half_open" # Testing recovery

class CircuitBreaker[T]:
    async def execute(self, func: Callable[[], Awaitable[T]]) -> T:
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
            else:
                raise CircuitOpenError()
        # ... execution logic
```

### Retry with Exponential Backoff

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)

class Retry[T]:
    async def execute(self, func: Callable[[], Awaitable[T]]) -> T:
        for attempt in range(self.config.max_attempts):
            try:
                return await func()
            except self.config.retryable_exceptions:
                if attempt == self.config.max_attempts - 1:
                    raise
                delay = self._calculate_delay(attempt)
                await asyncio.sleep(delay)
```

### Bulkhead (Concurrency Limiter)

```python
@dataclass
class BulkheadConfig:
    max_concurrent: int = 10
    max_wait: float = 5.0

class Bulkhead:
    def __init__(self, config: BulkheadConfig):
        self._semaphore = asyncio.Semaphore(config.max_concurrent)

    async def execute[T](self, func: Callable[[], Awaitable[T]]) -> T:
        try:
            await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self.config.max_wait,
            )
        except asyncio.TimeoutError:
            raise BulkheadFullError()
        try:
            return await func()
        finally:
            self._semaphore.release()
```

### Timeout

```python
@dataclass
class TimeoutConfig:
    timeout: float = 30.0

class Timeout:
    async def execute[T](self, func: Callable[[], Awaitable[T]]) -> T:
        return await asyncio.wait_for(func(), timeout=self.config.timeout)
```

### Composition

```python
# Combine patterns
resilient_call = (
    CircuitBreaker(circuit_config)
    .with_retry(retry_config)
    .with_timeout(timeout_config)
    .with_bulkhead(bulkhead_config)
)

result = await resilient_call.execute(external_api_call)
```

## Consequences

### Positive
- Prevents cascade failures
- Graceful degradation
- Resource protection
- Configurable per use case

### Negative
- Additional complexity
- Requires tuning per service
- May mask underlying issues

### Neutral
- Requires monitoring to tune thresholds
- Works best with observability

## Alternatives Considered

1. **No resilience patterns** - Rejected as system would be fragile
2. **External service mesh (Istio)** - Rejected as adds infrastructure complexity
3. **Library-only (tenacity)** - Rejected as doesn't provide circuit breaker

## References

- [src/infrastructure/resilience/patterns.py](../../src/infrastructure/resilience/patterns.py)
- [src/infrastructure/redis/circuit_breaker.py](../../src/infrastructure/redis/circuit_breaker.py)

## History

| Date | Status | Notes |
|------|--------|-------|
| 2024-12-02 | Proposed | Initial proposal |
| 2024-12-02 | Accepted | Approved for implementation |
