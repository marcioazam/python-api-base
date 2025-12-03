"""Resilience middleware for command bus.

Combined fault tolerance patterns: retry and circuit breaker.

**Feature: enterprise-features-2025**
**Validates: Requirements 11.1, 11.2, 11.3**
**Refactored: 2025 - Split into modular components for maintainability**
"""

from collections.abc import Awaitable, Callable
from typing import Any

from application.common.middleware.retry import RetryMiddleware, RetryConfig
from application.common.middleware.circuit_breaker import (
    CircuitBreakerMiddleware,
    CircuitBreakerConfig,
    CircuitState,
)


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
