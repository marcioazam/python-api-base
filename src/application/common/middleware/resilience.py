"""Resilience middleware for command bus.

Provides fault tolerance patterns:
- RetryMiddleware: Automatic retry with exponential backoff
- CircuitBreakerMiddleware: Fail-fast to prevent cascade failures

**Feature: enterprise-features-2025**
**Validates: Requirements 11.1, 11.2, 11.3**
"""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, UTC
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)


# =============================================================================
# Retry Middleware
# =============================================================================


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(
        self,
        message: str,
        attempts: int,
        last_error: Exception,
    ) -> None:
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = (
        TimeoutError,
        ConnectionError,
        OSError,
    )


class RetryMiddleware:
    """Middleware that retries failed commands with exponential backoff.

    Implements the retry pattern for transient failures with:
    - Exponential backoff between retries
    - Optional jitter to prevent thundering herd
    - Configurable retryable exceptions

    Example:
        >>> retry = RetryMiddleware(RetryConfig(max_retries=3))
        >>> bus.add_middleware(retry)
    """

    def __init__(self, config: RetryConfig | None = None) -> None:
        """Initialize retry middleware.

        Args:
            config: Retry configuration.
        """
        self._config = config or RetryConfig()

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the current attempt.

        Args:
            attempt: Current attempt number (0-indexed).

        Returns:
            Delay in seconds.
        """
        delay = self._config.base_delay * (self._config.exponential_base**attempt)
        delay = min(delay, self._config.max_delay)

        if self._config.jitter:
            delay *= 0.5 + random.random()

        return delay

    def _is_retryable(self, error: Exception) -> bool:
        """Check if an error should be retried.

        Args:
            error: The exception to check.

        Returns:
            True if the error is retryable.
        """
        return isinstance(error, self._config.retryable_exceptions)

    async def __call__(
        self,
        command: Any,
        next_handler: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """Execute command with retry logic.

        Args:
            command: The command to execute.
            next_handler: The next handler in the chain.

        Returns:
            Result from the handler.

        Raises:
            RetryExhaustedError: If all retries are exhausted.
        """
        command_type = type(command).__name__
        last_error: Exception | None = None

        for attempt in range(self._config.max_retries + 1):
            try:
                result = await next_handler(command)

                if attempt > 0:
                    logger.info(
                        f"Command {command_type} succeeded after {attempt + 1} attempts",
                        extra={
                            "command_type": command_type,
                            "attempts": attempt + 1,
                            "operation": "RETRY_SUCCESS",
                        },
                    )

                return result

            except Exception as e:
                last_error = e

                if not self._is_retryable(e):
                    logger.debug(
                        f"Non-retryable error for {command_type}: {type(e).__name__}"
                    )
                    raise

                if attempt < self._config.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"Command {command_type} failed (attempt {attempt + 1}), "
                        f"retrying in {delay:.2f}s: {e}",
                        extra={
                            "command_type": command_type,
                            "attempt": attempt + 1,
                            "delay_seconds": delay,
                            "error_type": type(e).__name__,
                            "operation": "RETRY_ATTEMPT",
                        },
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Command {command_type} failed after {attempt + 1} attempts",
                        extra={
                            "command_type": command_type,
                            "attempts": attempt + 1,
                            "operation": "RETRY_EXHAUSTED",
                        },
                    )

        raise RetryExhaustedError(
            message=f"Command {command_type} failed after {self._config.max_retries + 1} attempts",
            attempts=self._config.max_retries + 1,
            last_error=last_error,  # type: ignore
        )


# =============================================================================
# Circuit Breaker Middleware
# =============================================================================


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
                    from datetime import timedelta

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


# =============================================================================
# Combined Resilience Middleware
# =============================================================================


class ResilienceMiddleware:
    """Combined retry and circuit breaker middleware.

    Applies both patterns in the correct order:
    1. Circuit breaker (fail fast if service is down)
    2. Retry (retry transient failures)

    Example:
        >>> resilience = ResilienceMiddleware(
        ...     retry_config=RetryConfig(max_retries=3),
        ...     circuit_config=CircuitBreakerConfig(failure_threshold=5),
        ... )
        >>> bus.add_middleware(resilience)
    """

    def __init__(
        self,
        retry_config: RetryConfig | None = None,
        circuit_config: CircuitBreakerConfig | None = None,
    ) -> None:
        """Initialize resilience middleware.

        Args:
            retry_config: Retry configuration.
            circuit_config: Circuit breaker configuration.
        """
        self._retry = RetryMiddleware(retry_config)
        self._circuit_breaker = CircuitBreakerMiddleware(circuit_config)

    @property
    def circuit_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self._circuit_breaker.state

    async def __call__(
        self,
        command: Any,
        next_handler: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """Execute command with resilience patterns.

        Args:
            command: The command to execute.
            next_handler: The next handler in the chain.

        Returns:
            Result from the handler.
        """

        # Chain: circuit_breaker -> retry -> handler
        async def with_retry(cmd: Any) -> Any:
            return await self._retry(cmd, next_handler)

        return await self._circuit_breaker(command, with_retry)
