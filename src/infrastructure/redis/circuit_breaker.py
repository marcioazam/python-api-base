"""Circuit breaker pattern for Redis client.

**Feature: enterprise-infrastructure-2025**
**Requirement: R1.5 - Circuit breaker pattern
"""

from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker implementation for Redis operations.

    **Requirement: R1.5 - Circuit breaker pattern and fallback**

    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceeded threshold, requests fail fast
    - HALF_OPEN: Testing recovery, limited requests allowed

    Attributes:
        failure_threshold: Number of failures before opening
        reset_timeout: Seconds to wait before testing recovery
        half_open_max_calls: Max calls allowed in half-open state
    """

    failure_threshold: int = 5
    reset_timeout: float = 30.0
    half_open_max_calls: int = 1

    # Internal state
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _half_open_calls: int = field(default=0, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing)."""
        return self._state == CircuitState.OPEN

    async def can_execute(self) -> bool:
        """Check if request can be executed.

        Returns:
            True if request should proceed
        """
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # Check if timeout has elapsed
                if time.time() - self._last_failure_time >= self.reset_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                    return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

            return False

    async def record_success(self) -> None:
        """Record successful operation."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info("Circuit breaker CLOSED after successful recovery")
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    async def record_failure(self, error: Exception | None = None) -> None:
        """Record failed operation.

        Args:
            error: Optional exception that caused failure
        """
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker OPEN after half-open failure",
                    extra={"error": str(error) if error else None},
                )
            elif (
                self._state == CircuitState.CLOSED
                and self._failure_count >= self.failure_threshold
            ):
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker OPEN after threshold exceeded",
                    extra={
                        "failures": self._failure_count,
                        "threshold": self.failure_threshold,
                        "error": str(error) if error else None,
                    },
                )

    async def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_calls = 0
            logger.info("Circuit breaker manually reset")


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, message: str = "Circuit breaker is open") -> None:
        super().__init__(message)
