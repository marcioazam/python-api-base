"""Retry pattern with exponential backoff for resilient operations."""

import asyncio
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = field(
        default_factory=lambda: (Exception,)
    )


def calculate_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """Calculate delay for next retry attempt.
    
    Uses exponential backoff with optional jitter.
    
    Args:
        attempt: Current attempt number (0-indexed).
        config: Retry configuration.
        
    Returns:
        Delay in seconds.
    """
    delay = config.base_delay * (config.exponential_base ** attempt)
    delay = min(delay, config.max_delay)

    if config.jitter:
        # Add random jitter (±25%)
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)

    return max(0, delay)


async def retry_async[T, **P](
    func: Callable[P, T],
    *args: P.args,
    config: RetryConfig | None = None,
    **kwargs: P.kwargs,
) -> T:
    """Execute an async function with retry logic.
    
    Args:
        func: Async function to execute.
        *args: Positional arguments.
        config: Retry configuration.
        **kwargs: Keyword arguments.
        
    Returns:
        Function result.
        
    Raises:
        Exception: Last exception if all retries fail.
    """
    config = config or RetryConfig()
    last_exception: Exception | None = None

    for attempt in range(config.max_attempts):
        try:
            result = func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            return result
        except config.retryable_exceptions as e:
            last_exception = e

            if attempt < config.max_attempts - 1:
                delay = calculate_delay(attempt, config)
                logger.warning(
                    f"Retry attempt {attempt + 1}/{config.max_attempts} "
                    f"failed, retrying in {delay:.2f}s",
                    extra={
                        "attempt": attempt + 1,
                        "max_attempts": config.max_attempts,
                        "delay": delay,
                        "error": str(e),
                    },
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"All {config.max_attempts} retry attempts failed",
                    extra={
                        "max_attempts": config.max_attempts,
                        "error": str(e),
                    },
                )

    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected retry state")


def retry[T, **P](
    config: RetryConfig | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to add retry logic to a function.
    
    Args:
        config: Retry configuration.
        
    Returns:
        Decorated function.
    """
    config = config or RetryConfig()

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await retry_async(func, *args, config=config, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            import time

            last_exception: Exception | None = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e

                    if attempt < config.max_attempts - 1:
                        delay = calculate_delay(attempt, config)
                        logger.warning(
                            f"Retry attempt {attempt + 1}/{config.max_attempts} "
                            f"failed, retrying in {delay:.2f}s"
                        )
                        time.sleep(delay)

            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry state")

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


# Predefined configurations for common scenarios
RETRY_FAST = RetryConfig(
    max_attempts=3,
    base_delay=0.1,
    max_delay=1.0,
)

RETRY_STANDARD = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
)

RETRY_PERSISTENT = RetryConfig(
    max_attempts=5,
    base_delay=2.0,
    max_delay=60.0,
)
