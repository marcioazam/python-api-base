"""Timeout decorator for async functions.

Uses ParamSpec (PEP 612) to preserve function signatures.
"""

import asyncio
import functools
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


class TimeoutError(Exception):
    """Raised when operation times out."""

    def __init__(self, operation: str, timeout: float) -> None:
        self.operation = operation
        self.timeout = timeout
        super().__init__(f"Operation '{operation}' timed out after {timeout}s")


def timeout[T, **P](
    seconds: float,
    error_message: str | None = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Timeout decorator for async functions.

    Cancels the operation if it exceeds the specified timeout.

    Args:
        seconds: Maximum execution time in seconds.
        error_message: Custom error message (optional).

    Returns:
        Decorated function with timeout protection.

    Example:
        >>> @timeout(5.0)
        ... async def slow_operation() -> str:
        ...     await asyncio.sleep(10)
        ...     return "done"
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds,
                )
            except asyncio.TimeoutError as e:
                msg = error_message or func.__name__
                raise TimeoutError(msg, seconds) from e

        return wrapper

    return decorator


async def with_timeout[T](
    coro: Awaitable[T],
    seconds: float,
    operation_name: str = "operation",
) -> T:
    """Execute a coroutine with a timeout.

    Args:
        coro: Coroutine to execute.
        seconds: Maximum execution time in seconds.
        operation_name: Name for error messages.

    Returns:
        Result of the coroutine.

    Raises:
        TimeoutError: If operation exceeds timeout.

    Example:
        >>> result = await with_timeout(fetch_data(), 5.0, "fetch_data")
    """
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except asyncio.TimeoutError as e:
        raise TimeoutError(operation_name, seconds) from e
