"""Circuit breaker pattern for resilient external service calls.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.

**Feature: deep-code-quality-generics-review**
**Validates: Requirements 1.1**
"""

import asyncio
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    half_open_max_calls: int = 3


class CircuitBreakerError(Exception):
    """Raised when circuit is open."""

    def __init__(self, message: str = "Circuit breaker is open") -> None:
        super().__init__(message)


class CircuitBreaker:
    """Circuit breaker for external service calls.
    
    Prevents cascading failures by stopping calls to failing services.
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        """Initialize circuit breaker.
        
        Args:
            name: Name for logging/identification.
            config: Circuit breaker configuration.
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: datetime | None = None
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try resetting."""
        if self._last_failure_time is None:
            return True
        elapsed = datetime.now(UTC) - self._last_failure_time
        return elapsed >= self.config.timeout

    def _record_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._reset()
                logger.info(f"Circuit {self.name} closed after recovery")
        else:
            self._failure_count = 0

    def _record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now(UTC)

        if self._state == CircuitState.HALF_OPEN or self._failure_count >= self.config.failure_threshold:
            self._trip()

    def _trip(self) -> None:
        """Trip the circuit to open state."""
        self._state = CircuitState.OPEN
        self._success_count = 0
        logger.warning(f"Circuit {self.name} opened due to failures")

    def _reset(self) -> None:
        """Reset the circuit to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0

    def _can_execute(self) -> bool:
        """Check if a call can be executed."""
        state = self.state

        if state == CircuitState.CLOSED:
            return True

        if state == CircuitState.OPEN:
            return False

        # Half-open: allow limited calls
        if self._half_open_calls < self.config.half_open_max_calls:
            self._half_open_calls += 1
            return True

        return False

    async def call[T](
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute a function with circuit breaker protection.
        
        Args:
            func: Function to execute.
            *args: Positional arguments.
            **kwargs: Keyword arguments.
            
        Returns:
            Function result.
            
        Raises:
            CircuitBreakerError: If circuit is open.
        """
        if not self._can_execute():
            raise CircuitBreakerError(
                f"Circuit {self.name} is open, rejecting call"
            )

        try:
            result = func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            self._record_success()
            return result
        except Exception:
            self._record_failure()
            raise


def circuit_breaker[T](
    name: str,
    config: CircuitBreakerConfig | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to apply circuit breaker to a function.
    
    Uses PEP 695 type parameter syntax for cleaner generic definitions.
    
    Args:
        name: Circuit breaker name.
        config: Circuit breaker configuration.
        
    Returns:
        Decorated function.
    """
    cb = CircuitBreaker(name, config)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            return await cb.call(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            if not cb._can_execute():
                raise CircuitBreakerError(
                    f"Circuit {name} is open, rejecting call"
                )
            try:
                result = func(*args, **kwargs)
                cb._record_success()
                return result
            except Exception:
                cb._record_failure()
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


# Thread-safe registry of circuit breakers
# **Feature: shared-modules-security-fixes**
# **Validates: Requirements 5.1, 5.2, 5.3**


class CircuitBreakerRegistry:
    """Thread-safe singleton registry for circuit breakers.
    
    Provides thread-safe access to circuit breakers with test isolation support.
    """

    _instance: "CircuitBreakerRegistry | None" = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "CircuitBreakerRegistry":
        """Create or return singleton instance (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._breakers: dict[str, CircuitBreaker] = {}
                    instance._breakers_lock = threading.RLock()
                    cls._instance = instance
        return cls._instance

    def get(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        """Get or create circuit breaker (thread-safe).
        
        Args:
            name: Circuit breaker name.
            config: Configuration (only used if creating new).
            
        Returns:
            Circuit breaker instance.
        """
        with self._breakers_lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
            return self._breakers[name]

    def get_all(self) -> dict[str, CircuitBreaker]:
        """Get all registered circuit breakers (thread-safe).
        
        Returns:
            Copy of circuit breakers dictionary.
        """
        with self._breakers_lock:
            return self._breakers.copy()

    def reset(self) -> None:
        """Reset registry for testing (clears all breakers)."""
        with self._breakers_lock:
            self._breakers.clear()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance for test isolation."""
        with cls._lock:
            cls._instance = None


# Module-level registry instance
_registry: CircuitBreakerRegistry | None = None


def _get_registry() -> CircuitBreakerRegistry:
    """Get the global registry instance."""
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry()
    return _registry


def get_circuit_breaker(
    name: str,
    config: CircuitBreakerConfig | None = None,
) -> CircuitBreaker:
    """Get or create a circuit breaker by name.
    
    Args:
        name: Circuit breaker name.
        config: Configuration (only used if creating new).
        
    Returns:
        Circuit breaker instance.
    """
    return _get_registry().get(name, config)


def get_all_circuit_breakers() -> dict[str, CircuitBreaker]:
    """Get all registered circuit breakers.
    
    Returns:
        Dictionary of circuit breakers by name.
    """
    return _get_registry().get_all()


def reset_circuit_breaker_registry() -> None:
    """Reset the circuit breaker registry for testing."""
    global _registry
    if _registry is not None:
        _registry.reset()
    CircuitBreakerRegistry.reset_instance()
    _registry = None
