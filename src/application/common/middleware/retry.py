"""Retry middleware with exponential backoff.

**Feature: enterprise-features-2025**
**Validates: Requirement 11.1 - Automatic retry with exponential backoff**
"""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


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
