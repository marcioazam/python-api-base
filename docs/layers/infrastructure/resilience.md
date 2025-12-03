# Resilience Patterns

## Overview

Padrões de resiliência para tolerância a falhas em chamadas a serviços externos.

## Circuit Breaker

```python
from enum import Enum
from dataclasses import dataclass

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5      # Failures to open
    success_threshold: int = 3      # Successes to close
    timeout: float = 30.0           # Seconds in half-open

class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig):
        self._config = config
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
    
    async def execute[T](self, func: Callable[[], Awaitable[T]]) -> T:
        if self._state == CircuitState.OPEN:
            if self._should_try_reset():
                self._state = CircuitState.HALF_OPEN
            else:
                raise CircuitOpenError("Circuit is open")
        
        try:
            result = await func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._config.success_threshold:
                self._state = CircuitState.CLOSED
                self._reset_counts()
        else:
            self._reset_counts()
    
    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
        elif self._failure_count >= self._config.failure_threshold:
            self._state = CircuitState.OPEN
```

## Retry Pattern

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)

class Retry:
    def __init__(self, config: RetryConfig):
        self._config = config
    
    async def execute[T](self, func: Callable[[], Awaitable[T]]) -> T:
        last_exception: Exception | None = None
        
        for attempt in range(self._config.max_attempts):
            try:
                return await func()
            except self._config.retryable_exceptions as e:
                last_exception = e
                if attempt < self._config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    await asyncio.sleep(delay)
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        delay = self._config.base_delay * (self._config.exponential_base ** attempt)
        delay = min(delay, self._config.max_delay)
        
        if self._config.jitter:
            delay *= random.uniform(0.5, 1.5)
        
        return delay
```

## Bulkhead (Concurrency Limiter)

```python
@dataclass
class BulkheadConfig:
    max_concurrent: int = 10
    max_wait: float = 5.0

class Bulkhead:
    def __init__(self, config: BulkheadConfig):
        self._config = config
        self._semaphore = asyncio.Semaphore(config.max_concurrent)
    
    async def execute[T](self, func: Callable[[], Awaitable[T]]) -> T:
        try:
            await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self._config.max_wait,
            )
        except asyncio.TimeoutError:
            raise BulkheadRejectedError("Max concurrent requests reached")
        
        try:
            return await func()
        finally:
            self._semaphore.release()
```

## Timeout

```python
class Timeout:
    def __init__(self, timeout: float):
        self._timeout = timeout
    
    async def execute[T](self, func: Callable[[], Awaitable[T]]) -> T:
        try:
            return await asyncio.wait_for(func(), timeout=self._timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {self._timeout}s")
```

## Composing Patterns

```python
class ResilientClient:
    def __init__(self):
        self._circuit = CircuitBreaker(CircuitBreakerConfig(failure_threshold=5))
        self._retry = Retry(RetryConfig(max_attempts=3))
        self._bulkhead = Bulkhead(BulkheadConfig(max_concurrent=10))
        self._timeout = Timeout(timeout=30.0)
    
    async def call[T](self, func: Callable[[], Awaitable[T]]) -> T:
        return await self._circuit.execute(
            lambda: self._retry.execute(
                lambda: self._timeout.execute(
                    lambda: self._bulkhead.execute(func)
                )
            )
        )

# Usage
client = ResilientClient()
result = await client.call(lambda: http_client.get("/api/data"))
```

## Decorator Usage

```python
@circuit_breaker(failure_threshold=5, timeout=30)
@retry(max_attempts=3, base_delay=1.0)
@timeout(seconds=10)
async def call_external_api(endpoint: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint)
        return response.json()
```

## Best Practices

1. **Configure per service** - Different services need different settings
2. **Monitor circuit state** - Alert on open circuits
3. **Use jitter** - Prevent thundering herd
4. **Set reasonable timeouts** - Don't wait forever
5. **Log failures** - For debugging and alerting
