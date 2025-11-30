"""Timeout Middleware for request timeout handling.

This module provides timeout middleware for protecting against
slow requests with configurable per-endpoint timeouts.

**Feature: api-architecture-analysis**
**Validates: Requirements 6.4**
"""

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
from typing import Any
from collections.abc import Awaitable, Callable


class TimeoutAction(Enum):
    """Action to take when timeout occurs."""

    CANCEL = "cancel"
    RETURN_DEFAULT = "return_default"
    RAISE = "raise"


class TimeoutError(Exception):
    """Exception raised when request times out."""

    def __init__(
        self,
        message: str = "Request timed out",
        timeout: float = 0,
        endpoint: str = "",
    ) -> None:
        super().__init__(message)
        self.timeout = timeout
        self.endpoint = endpoint


@dataclass
class TimeoutConfig:
    """Configuration for timeout handling."""

    default_timeout: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    endpoint_timeouts: dict[str, timedelta] = field(default_factory=dict)
    action: TimeoutAction = TimeoutAction.RAISE
    default_response: Any = None
    log_timeouts: bool = True


@dataclass
class TimeoutResult[ResponseT]:
    """Result of a timeout-protected operation."""

    success: bool
    response: ResponseT | None = None
    timed_out: bool = False
    elapsed: float = 0.0
    error: Exception | None = None

    @classmethod
    def ok(cls, response: ResponseT, elapsed: float) -> "TimeoutResult[ResponseT]":
        """Create successful result."""
        return cls(success=True, response=response, elapsed=elapsed)

    @classmethod
    def timeout(cls, elapsed: float) -> "TimeoutResult[ResponseT]":
        """Create timeout result."""
        return cls(success=False, timed_out=True, elapsed=elapsed)

    @classmethod
    def failed(cls, error: Exception, elapsed: float) -> "TimeoutResult[ResponseT]":
        """Create failed result."""
        return cls(success=False, error=error, elapsed=elapsed)


class TimeoutMiddleware[RequestT, ResponseT]:
    """Middleware that enforces request timeouts."""

    def __init__(self, config: TimeoutConfig | None = None) -> None:
        self._config = config or TimeoutConfig()

    def get_timeout(self, endpoint: str) -> float:
        """Get timeout for endpoint in seconds."""
        if endpoint in self._config.endpoint_timeouts:
            return self._config.endpoint_timeouts[endpoint].total_seconds()
        return self._config.default_timeout.total_seconds()

    async def execute(
        self,
        handler: Callable[[], Awaitable[ResponseT]],
        endpoint: str = "",
    ) -> TimeoutResult[ResponseT]:
        """Execute handler with timeout."""
        timeout = self.get_timeout(endpoint)
        start_time = asyncio.get_event_loop().time()

        try:
            response = await asyncio.wait_for(handler(), timeout=timeout)
            elapsed = asyncio.get_event_loop().time() - start_time
            return TimeoutResult.ok(response, elapsed)
        except asyncio.TimeoutError:
            elapsed = asyncio.get_event_loop().time() - start_time
            if self._config.action == TimeoutAction.RAISE:
                raise TimeoutError(
                    f"Request to {endpoint} timed out after {timeout}s",
                    timeout=timeout,
                    endpoint=endpoint,
                )
            elif self._config.action == TimeoutAction.RETURN_DEFAULT:
                return TimeoutResult(
                    success=True,
                    response=self._config.default_response,
                    timed_out=True,
                    elapsed=elapsed,
                )
            return TimeoutResult.timeout(elapsed)
        except Exception as e:
            elapsed = asyncio.get_event_loop().time() - start_time
            return TimeoutResult.failed(e, elapsed)

    async def __call__(
        self,
        request: RequestT,
        next_handler: Callable[[RequestT], Awaitable[ResponseT]],
        endpoint: str = "",
    ) -> ResponseT:
        """Execute as middleware."""
        result = await self.execute(lambda: next_handler(request), endpoint)

        if result.timed_out and self._config.action == TimeoutAction.RAISE:
            raise TimeoutError(endpoint=endpoint)

        if result.error:
            raise result.error

        return result.response  # type: ignore


class TimeoutConfigBuilder:
    """Fluent builder for TimeoutConfig."""

    def __init__(self) -> None:
        self._default_timeout = timedelta(seconds=30)
        self._endpoint_timeouts: dict[str, timedelta] = {}
        self._action = TimeoutAction.RAISE
        self._default_response: Any = None
        self._log_timeouts = True

    def with_default_timeout(self, timeout: timedelta) -> "TimeoutConfigBuilder":
        """Set default timeout."""
        self._default_timeout = timeout
        return self

    def with_default_timeout_seconds(self, seconds: float) -> "TimeoutConfigBuilder":
        """Set default timeout in seconds."""
        self._default_timeout = timedelta(seconds=seconds)
        return self

    def for_endpoint(self, endpoint: str, timeout: timedelta) -> "TimeoutConfigBuilder":
        """Set timeout for specific endpoint."""
        self._endpoint_timeouts[endpoint] = timeout
        return self

    def for_endpoint_seconds(self, endpoint: str, seconds: float) -> "TimeoutConfigBuilder":
        """Set timeout for specific endpoint in seconds."""
        self._endpoint_timeouts[endpoint] = timedelta(seconds=seconds)
        return self

    def with_action(self, action: TimeoutAction) -> "TimeoutConfigBuilder":
        """Set timeout action."""
        self._action = action
        return self

    def with_default_response(self, response: Any) -> "TimeoutConfigBuilder":
        """Set default response for RETURN_DEFAULT action."""
        self._default_response = response
        return self

    def with_logging(self, enabled: bool = True) -> "TimeoutConfigBuilder":
        """Enable/disable timeout logging."""
        self._log_timeouts = enabled
        return self

    def build(self) -> TimeoutConfig:
        """Build the configuration."""
        return TimeoutConfig(
            default_timeout=self._default_timeout,
            endpoint_timeouts=self._endpoint_timeouts,
            action=self._action,
            default_response=self._default_response,
            log_timeouts=self._log_timeouts,
        )


def timeout_decorator[ResponseT](
    timeout_seconds: float,
    action: TimeoutAction = TimeoutAction.RAISE,
) -> Callable[[Callable[..., Awaitable[ResponseT]]], Callable[..., Awaitable[ResponseT]]]:
    """Decorator to add timeout to async functions."""
    def decorator(func: Callable[..., Awaitable[ResponseT]]) -> Callable[..., Awaitable[ResponseT]]:
        async def wrapper(*args: Any, **kwargs: Any) -> ResponseT:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                if action == TimeoutAction.RAISE:
                    raise TimeoutError(
                        f"Function {func.__name__} timed out after {timeout_seconds}s",
                        timeout=timeout_seconds,
                    )
                raise
        return wrapper
    return decorator


# Convenience factory
def create_timeout_middleware(
    config: TimeoutConfig | None = None,
) -> TimeoutMiddleware[Any, Any]:
    """Create a TimeoutMiddleware with defaults."""
    return TimeoutMiddleware(config=config)
