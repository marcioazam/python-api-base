"""HTTP client resilience patterns: circuit breaker and retry logic.

**Feature: enterprise-generics-2025**
**Requirement: R9.4 - Circuit breaker integration**
**Requirement: R9.5 - Retry with exponential backoff**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True, slots=True)
class RetryPolicy[TRequest]:
    """Retry policy configuration.

    **Requirement: R9.5 - Typed RetryPolicy[TRequest]**

    Type Parameters:
        TRequest: Request type this policy applies to.
    """

    max_retries: int = 3
    base_delay: timedelta = field(default_factory=lambda: timedelta(seconds=1))
    max_delay: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    exponential_base: float = 2.0
    retry_on_status: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 500, 502, 503, 504})
    )

    def get_delay(self, attempt: int) -> timedelta:
        """Calculate delay for retry attempt.

        Args:
            attempt: Current attempt number (0-based).

        Returns:
            Delay before next retry.
        """
        delay_seconds = self.base_delay.total_seconds() * (
            self.exponential_base**attempt
        )
        return timedelta(seconds=min(delay_seconds, self.max_delay.total_seconds()))


@dataclass(frozen=True, slots=True)
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = 5
    success_threshold: int = 3
    timeout: timedelta = field(default_factory=lambda: timedelta(seconds=30))


@dataclass
class HttpClientConfig:
    """HTTP client configuration.

    **Requirement: R9 - Client configuration**
    """

    base_url: str = ""
    timeout: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    headers: dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True


class CircuitBreaker:
    """Circuit breaker for HTTP client.

    **Requirement: R9.4 - CircuitBreaker[TRequest, TResponse]**
    """

    def __init__(self, config: CircuitBreakerConfig) -> None:
        self._config = config
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit allows requests."""
        if self._state == CircuitState.OPEN:
            # Check if timeout has passed
            if self._last_failure_time is not None:
                import time

                elapsed = time.time() - self._last_failure_time
                if elapsed >= self._config.timeout.total_seconds():
                    self._state = CircuitState.HALF_OPEN
                    return True
            return False
        return True

    def record_success(self) -> None:
        """Record successful request."""
        self._failure_count = 0
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._config.success_threshold:
                self._state = CircuitState.CLOSED
                self._success_count = 0

    def record_failure(self) -> None:
        """Record failed request."""
        import time

        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self._config.failure_threshold:
            self._state = CircuitState.OPEN
            self._success_count = 0
