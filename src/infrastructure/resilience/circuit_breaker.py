"""Circuit Breaker pattern implementation.

Implements the circuit breaker pattern with CLOSED → OPEN → HALF_OPEN → CLOSED states.
Uses ParamSpec (PEP 612) to preserve function signatures.
"""

import asyncio
import functools
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitOpenError(Exception):
    """Raised when circuit is open and request is rejected."""

    def __init__(self, circuit_name: str, time_until_retry: float) -> None:
        self.circuit_name = circuit_name
        self.time_until_retry = time_until_retry
        super().__init__(
            f"Circuit '{circuit_name}' is open. Retry in {time_until_retry:.1f}s"
        )


@dataclass
class CircuitBreakerState:
    """Internal state for circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_state_change: float = field(default_factory=time.time)


class CircuitBreaker:
    """Circuit breaker implementation.

    Tracks failures and opens the circuit when threshold is exceeded.
    After recovery_timeout, allows a test request (half-open state).
    If test succeeds, closes circuit; if fails, reopens.

    Attributes:
        name: Identifier for this circuit breaker.
        failure_threshold: Number of failures before opening circuit.
        success_threshold: Number of successes in half-open to close circuit.
        recovery_timeout: Seconds to wait before testing recovery.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        recovery_timeout: float = 30.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitBreakerState()
        self._lock = Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state.state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._state.failure_count

    def _should_allow_request(self) -> bool:
        """Check if request should be allowed based on current state."""
        with self._lock:
            if self._state.state == CircuitState.CLOSED:
                return True

            if self._state.state == CircuitState.OPEN:
                time_since_failure = time.time() - self._state.last_failure_time
                if time_since_failure >= self.recovery_timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
                    return True
                return False

            # HALF_OPEN: allow limited requests
            return True

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state.state
        self._state.state = new_state
        self._state.last_state_change = time.time()

        if new_state == CircuitState.CLOSED:
            self._state.failure_count = 0
            self._state.success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._state.success_count = 0

        logger.info(
            "Circuit state changed",
            extra={
                "circuit": self.name,
                "from_state": old_state.value,
                "to_state": new_state.value,
            },
        )

    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            if self._state.state == CircuitState.HALF_OPEN:
                self._state.success_count += 1
                if self._state.success_count >= self.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

    def record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            self._state.failure_count += 1
            self._state.last_failure_time = time.time()

            if self._state.state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)
            elif self._state.state == CircuitState.CLOSED:
                if self._state.failure_count >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

    def get_time_until_retry(self) -> float:
        """Get seconds until circuit can be tested again."""
        if self._state.state != CircuitState.OPEN:
            return 0.0
        elapsed = time.time() - self._state.last_failure_time
        return max(0.0, self.recovery_timeout - elapsed)

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitBreakerState()


# Global registry of circuit breakers
_circuit_breakers: dict[str, CircuitBreaker] = {}
_registry_lock = Lock()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    success_threshold: int = 2,
    recovery_timeout: float = 30.0,
) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                success_threshold=success_threshold,
                recovery_timeout=recovery_timeout,
            )
        return _circuit_breakers[name]


def circuit_breaker[T, **P](
    name: str | None = None,
    failure_threshold: int = 5,
    success_threshold: int = 2,
    recovery_timeout: float = 30.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    fallback: Callable[P, T] | Callable[P, Awaitable[T]] | None = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Circuit breaker decorator for async functions.

    Args:
        name: Circuit breaker name (defaults to function name).
        failure_threshold: Failures before opening circuit.
        success_threshold: Successes in half-open to close circuit.
        recovery_timeout: Seconds before testing recovery.
        exceptions: Exception types that count as failures.
        fallback: Optional fallback function when circuit is open.

    Returns:
        Decorated function with circuit breaker protection.

    Example:
        >>> @circuit_breaker(name="external_api", failure_threshold=3)
        ... async def call_external_api(url: str) -> dict:
        ...     return await http_client.get(url)
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        circuit_name = name or func.__name__
        cb = get_circuit_breaker(
            circuit_name, failure_threshold, success_threshold, recovery_timeout
        )

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if not cb._should_allow_request():
                if fallback is not None:
                    result = fallback(*args, **kwargs)
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
                raise CircuitOpenError(circuit_name, cb.get_time_until_retry())

            try:
                result = await func(*args, **kwargs)
                cb.record_success()
                return result
            except exceptions as e:
                cb.record_failure()
                raise

        return wrapper

    return decorator
