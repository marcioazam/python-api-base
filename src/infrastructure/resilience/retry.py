"""Retry decorator with exponential backoff.

Uses ParamSpec (PEP 612) to preserve function signatures.
"""

import asyncio
import functools
import logging
import random
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, attempts: int, last_exception: Exception) -> None:
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(f"Retry exhausted after {attempts} attempts: {last_exception}")


def retry[T, **P](
    max_attempts: int = 3,
    backoff_base: float = 1.0,
    backoff_max: float = 60.0,
    backoff_jitter: float = 0.1,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Retry decorator with exponential backoff for async functions.

    Preserves function signature using ParamSpec (PEP 612).

    Args:
        max_attempts: Maximum number of retry attempts (default: 3).
        backoff_base: Base delay in seconds for exponential backoff (default: 1.0).
        backoff_max: Maximum delay in seconds (default: 60.0).
        backoff_jitter: Random jitter factor (0-1) to add to delay (default: 0.1).
        exceptions: Tuple of exception types to catch and retry (default: all).
        on_retry: Optional callback called on each retry with (attempt, exception).

    Returns:
        Decorated function with retry logic.

    Example:
        >>> @retry(max_attempts=3, backoff_base=1.0, exceptions=(ConnectionError,))
        ... async def fetch_data(url: str) -> dict:
        ...     return await http_client.get(url)
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            "Retry exhausted",
                            extra={
                                "function": func.__name__,
                                "attempts": attempt,
                                "error": str(e),
                            },
                        )
                        raise RetryExhaustedError(attempt, e) from e

                    # Calculate delay with exponential backoff
                    delay = min(backoff_base * (2 ** (attempt - 1)), backoff_max)

                    # Add jitter
                    if backoff_jitter > 0:
                        jitter = delay * backoff_jitter * random.random()
                        delay += jitter

                    logger.warning(
                        "Retrying after error",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "delay": delay,
                            "error": str(e),
                        },
                    )

                    if on_retry:
                        on_retry(attempt, e)

                    await asyncio.sleep(delay)

            # Should never reach here, but satisfy type checker
            raise RetryExhaustedError(max_attempts, last_exception or Exception("Unknown error"))

        return wrapper

    return decorator


def retry_sync[T, **P](
    max_attempts: int = 3,
    backoff_base: float = 1.0,
    backoff_max: float = 60.0,
    backoff_jitter: float = 0.1,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Retry decorator with exponential backoff for sync functions.

    Same as retry() but for synchronous functions.
    """
    import time

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        raise RetryExhaustedError(attempt, e) from e

                    delay = min(backoff_base * (2 ** (attempt - 1)), backoff_max)
                    if backoff_jitter > 0:
                        delay += delay * backoff_jitter * random.random()

                    if on_retry:
                        on_retry(attempt, e)

                    time.sleep(delay)

            raise RetryExhaustedError(max_attempts, last_exception or Exception("Unknown error"))

        return wrapper

    return decorator
