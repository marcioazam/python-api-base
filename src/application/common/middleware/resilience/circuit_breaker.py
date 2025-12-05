"""Circuit breaker middleware for fault tolerance.

**Feature: enterprise-features-2025**
**Validates: Requirement 11.2 - Circuit breaker to prevent cascade failures**
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, message: str, recovery_time: datetime) -> None:
        self.recovery_time = recovery_time
        super().__init__(message)


@dataclass(slots=True)
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 1
    monitored_exceptions: tuple[type[Exception], ...] = (Exception,)


@dataclass(slots=True)
class CircuitBreakerStats:
    """Statistics for circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: datetime | None = None
    half_open_calls: int = 0


class CircuitBreakerMiddleware:
    """Middleware that implements circuit breaker pattern.

    Prevents cascade failures by failing fast when a service
    is experiencing issues. States:

    - CLOSED: Normal operation, requests pass through
    - OPEN: Failing fast, requests rejected immediately
    - HALF_OPEN: Testing recovery, limited requests allowed

    Example:
        >>> cb = CircuitBreakerMiddleware(
        ...     CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60)
        ... )
        >>> bus.add_middleware(cb)
    """

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        """Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration.
        """
        self._config = config or CircuitBreakerConfig()
        self._stats = CircuitBreakerStats()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._stats.state

    @property
    def stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics."""
        return self._stats

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset.

        Returns:
            True if recovery timeout has passed.
        """
        if self._stats.last_failure_time is None:
            return False

        elapsed = (datetime.now(UTC) - self._stats.last_failure_time).total_seconds()
        return elapsed >= self._config.recovery_timeout

    def _on_success(self) -> None:
        """Handle successful call."""
        if self._stats.state == CircuitState.HALF_OPEN:
            logger.info(
                "Circuit breaker recovered, closing circuit",
                extra={"operation": "CIRCUIT_CLOSED"},
            )

        self._stats.failure_count = 0
        self._stats.success_count += 1
        self._stats.state = CircuitState.CLOSED
        self._stats.half_open_calls = 0

    def _on_failure(self, error: Exception) -> None:
        """Handle failed call.

        Args:
            error: The exception that occurred.
        """
        self._stats.failure_count += 1
        self._stats.last_failure_time = datetime.now(UTC)

        if self._stats.failure_count >= self._config.failure_threshold:
            logger.warning(
                f"Circuit breaker opened after {self._stats.failure_count} failures",
                extra={
                    "failure_count": self._stats.failure_count,
                    "recovery_timeout": self._config.recovery_timeout,
                    "operation": "CIRCUIT_OPENED",
                },
            )
            self._stats.state = CircuitState.OPEN

    def _is_monitored_exception(self, error: Exception) -> bool:
        """Check if exception should trip the circuit.

        Args:
            error: The exception to check.

        Returns:
            True if exception should count as failure.
        """
        return isinstance(error, self._config.monitored_exceptions)

    async def __call__(
        self,
        command: Any,
        next_handler: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """Execute command with circuit breaker protection.

        Args:
            command: The command to execute.
            next_handler: The next handler in the chain.

        Returns:
            Result from the handler.

        Raises:
            CircuitBreakerOpenError: If circuit is open.
        """
        command_type = type(command).__name__

        # Check if circuit is open
        if self._stats.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(
                    "Circuit breaker entering half-open state",
                    extra={"operation": "CIRCUIT_HALF_OPEN"},
                )
                self._stats.state = CircuitState.HALF_OPEN
                self._stats.half_open_calls = 0
            else:
                recovery_time = self._stats.last_failure_time
                if recovery_time:
                    recovery_time += timedelta(seconds=self._config.recovery_timeout)

                raise CircuitBreakerOpenError(
                    message=f"Circuit breaker is open for {command_type}",
                    recovery_time=recovery_time or datetime.now(UTC),
                )

        # Check half-open limit
        if self._stats.state == CircuitState.HALF_OPEN:
            if self._stats.half_open_calls >= self._config.half_open_max_calls:
                raise CircuitBreakerOpenError(
                    message=f"Circuit breaker half-open limit reached for {command_type}",
                    recovery_time=datetime.now(UTC),
                )
            self._stats.half_open_calls += 1

        # Execute command
        try:
            result = await next_handler(command)
            self._on_success()
            return result

        except Exception as e:
            if self._is_monitored_exception(e):
                self._on_failure(e)
            raise
