"""Circuit breaker pattern implementation.

**Feature: infrastructure-modules-workflow-analysis**
**Validates: Requirements 1.3**

This module provides circuit breaker pattern for fault tolerance.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import TypeVar

from core.base.patterns.result import Err, Ok, Result


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: timedelta = timedelta(seconds=30)
    half_open_max_calls: int = 3


T = TypeVar("T")


class CircuitBreaker:
    """Circuit breaker for fault tolerance.

    **Feature: infrastructure-modules-workflow-analysis**
    **Validates: Requirements 1.3**
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None) -> None:
        self.name = name
        self._config = config or CircuitBreakerConfig()
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
            elapsed = datetime.now(timezone.utc) - self._last_failure_time
            if elapsed >= self._config.timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self._success_count = 0

    def _record_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._config.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
        else:
            self._failure_count = 0

    def _record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now(timezone.utc)
        
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
        elif self._failure_count >= self._config.failure_threshold:
            self._state = CircuitState.OPEN

    def _can_execute(self) -> bool:
        """Check if a call can be executed."""
        self._check_timeout()
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls < self._config.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False
        return False

    async def execute(
        self,
        func: Callable[[], Awaitable[T]],
    ) -> Result[T, Exception]:
        """Execute function with circuit breaker protection."""
        if not self._can_execute():
            return Err(Exception(f"Circuit '{self.name}' is open"))

        try:
            result = await func()
            self._record_success()
            return Ok(result)
        except Exception as e:
            self._record_failure()
            return Err(e)


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
]
