"""Generic resilience patterns with PEP 695 type parameters.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5**
"""

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol, runtime_checkable

from core.base.patterns.result import Err, Ok, Result


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True, slots=True)
class CircuitBreakerConfig[TThreshold]:
    """Generic circuit breaker configuration.

    Type Parameters:
        TThreshold: Type for failure threshold (int, float, or custom).

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 16.1**
    """

    failure_threshold: TThreshold
    success_threshold: int = 3
    timeout_seconds: float = 30.0
    half_open_max_calls: int = 3


class CircuitBreaker[TConfig: CircuitBreakerConfig]:
    """Generic circuit breaker with typed configuration.

    Type Parameters:
        TConfig: Configuration type extending CircuitBreakerConfig.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 16.1**
    """

    def __init__(self, config: TConfig) -> None:
        self._config = config
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: datetime | None = None
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        self._check_timeout()
        return self._state

    def _check_timeout(self) -> None:
        """Check if timeout has passed to transition from OPEN to HALF_OPEN."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            elapsed = datetime.now() - self._last_failure_time
            if elapsed.total_seconds() >= self._config.timeout_seconds:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._config.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
        else:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        threshold = self._config.failure_threshold
        if isinstance(threshold, int) and self._failure_count >= threshold:
            self._state = CircuitState.OPEN
        elif self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN

    def can_execute(self) -> bool:
        """Check if a call can be executed."""
        self._check_timeout()
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self._config.half_open_max_calls
        return False

    async def execute[T](
        self,
        func: Callable[[], Awaitable[T]],
    ) -> Result[T, Exception]:
        """Execute function with circuit breaker protection.

        Returns:
            Ok with result or Err with exception.
        """
        if not self.can_execute():
            return Err(Exception("Circuit is open"))

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1

        try:
            result = await func()
            self.record_success()
            return Ok(result)
        except Exception as e:
            self.record_failure()
            return Err(e)


@dataclass(frozen=True, slots=True)
class RetryConfig:
    """Configuration for retry behavior.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 16.2**
    """

    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


@runtime_checkable
class BackoffStrategy(Protocol):
    """Protocol for backoff strategies."""

    def get_delay(self, attempt: int) -> float:
        """Get delay for given attempt number."""
        ...


class ExponentialBackoff:
    """Exponential backoff with optional jitter.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 16.2**
    """

    def __init__(self, config: RetryConfig) -> None:
        self._config = config

    def get_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff."""
        delay = self._config.base_delay_seconds * (
            self._config.exponential_base ** (attempt - 1)
        )
        delay = min(delay, self._config.max_delay_seconds)
        if self._config.jitter:
            delay = delay * (0.5 + random.random())
        return delay


class Retry[T]:
    """Generic retry wrapper with typed result.

    Type Parameters:
        T: The return type of the retried operation.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 16.2**
    """

    def __init__(
        self,
        config: RetryConfig | None = None,
        backoff: BackoffStrategy | None = None,
    ) -> None:
        self._config = config or RetryConfig()
        self._backoff = backoff or ExponentialBackoff(self._config)

    async def execute(
        self,
        func: Callable[[], Awaitable[T]],
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> Result[T, Exception]:
        """Execute with retry logic.

        Args:
            func: Async function to execute.
            retryable_exceptions: Exception types that trigger retry.

        Returns:
            Ok with result or Err with last exception.
        """
        last_error: Exception | None = None

        for attempt in range(1, self._config.max_attempts + 1):
            try:
                result = await func()
                return Ok(result)
            except retryable_exceptions as e:
                last_error = e
                if attempt < self._config.max_attempts:
                    delay = self._backoff.get_delay(attempt)
                    await asyncio.sleep(delay)

        return Err(last_error or Exception("All retries failed"))


@dataclass(frozen=True, slots=True)
class TimeoutConfig:
    """Timeout configuration."""

    duration_seconds: float
    message: str = "Operation timed out"


class Timeout[T]:
    """Generic timeout wrapper.

    Type Parameters:
        T: The return type of the timed operation.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 16.3**
    """

    def __init__(self, config: TimeoutConfig) -> None:
        self._config = config

    async def execute(
        self,
        func: Callable[[], Awaitable[T]],
    ) -> Result[T, TimeoutError]:
        """Execute with timeout.

        Returns:
            Ok with result or Err with TimeoutError.
        """
        try:
            result = await asyncio.wait_for(
                func(),
                timeout=self._config.duration_seconds,
            )
            return Ok(result)
        except asyncio.TimeoutError:
            return Err(TimeoutError(self._config.message))


class Fallback[T, TFallback]:
    """Generic fallback pattern for graceful degradation.

    Type Parameters:
        T: Primary operation return type.
        TFallback: Fallback value type.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 16.4**
    """

    def __init__(
        self,
        fallback_value: TFallback | None = None,
        fallback_func: Callable[[], Awaitable[TFallback]] | None = None,
    ) -> None:
        self._fallback_value = fallback_value
        self._fallback_func = fallback_func

    async def execute(
        self,
        func: Callable[[], Awaitable[T]],
    ) -> T | TFallback:
        """Execute with fallback on failure.

        Returns:
            Primary result or fallback value.
        """
        try:
            return await func()
        except Exception:
            if self._fallback_func:
                return await self._fallback_func()
            if self._fallback_value is not None:
                return self._fallback_value
            raise


@dataclass
class BulkheadConfig:
    """Bulkhead configuration for resource isolation."""

    max_concurrent: int = 10
    max_wait_seconds: float = 5.0


class Bulkhead[T]:
    """Generic bulkhead for resource isolation.

    Type Parameters:
        T: The return type of isolated operations.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 16.5**
    """

    def __init__(self, config: BulkheadConfig) -> None:
        self._config = config
        self._semaphore = asyncio.Semaphore(config.max_concurrent)
        self._rejected_count = 0

    @property
    def rejected_count(self) -> int:
        """Get count of rejected calls."""
        return self._rejected_count

    async def execute(
        self,
        func: Callable[[], Awaitable[T]],
    ) -> Result[T, Exception]:
        """Execute with bulkhead isolation.

        Returns:
            Ok with result or Err if rejected.
        """
        try:
            acquired = await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self._config.max_wait_seconds,
            )
            if not acquired:
                self._rejected_count += 1
                return Err(Exception("Bulkhead rejected: max concurrent reached"))
        except asyncio.TimeoutError:
            self._rejected_count += 1
            return Err(Exception("Bulkhead rejected: wait timeout"))

        try:
            result = await func()
            return Ok(result)
        finally:
            self._semaphore.release()
