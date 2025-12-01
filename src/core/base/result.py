"""Result pattern for explicit error handling.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.
Implements monadic operations for functional error handling.

**Feature: python-api-base-2025-state-of-art**
**Validates: Requirements 3.1, 3.2, 3.4**
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Ok[T]:
    """Represents a successful result.

    Type Parameters:
        T: The type of the success value.

    **Feature: ultimate-generics-code-review-2025**
    **Validates: Requirements 5.1, 15.1**
    """

    value: T

    def is_ok(self) -> bool:
        """Check if result is Ok."""
        return True

    def to_dict(self) -> dict[str, Any]:
        """Serialize Ok to dictionary for round-trip testing.

        **Feature: ultimate-generics-code-review-2025, Property 2: Result Pattern Round-Trip**
        **Validates: Requirements 15.1**

        Returns:
            Dictionary with type discriminator and value.
        """
        return {"type": "Ok", "value": self.value}

    def is_err(self) -> bool:
        """Check if result is Err."""
        return False

    def unwrap(self) -> T:
        """Get the value, raises if Err."""
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Get the value or return default."""
        return self.value

    def unwrap_or_else(self, fn: Callable[[], T]) -> T:
        """Get the value or compute default from function."""
        return self.value

    def expect(self, msg: str) -> T:
        """Get the value or raise with custom message."""
        return self.value

    def map[U](self, fn: Callable[[T], U]) -> "Ok[U]":
        """Apply function to value."""
        return Ok(fn(self.value))

    def bind[U, F](self, fn: Callable[[T], "Result[U, F]"]) -> "Result[U, F]":
        """Monadic bind (flatMap) - chain operations that return Result.

        Args:
            fn: Function that takes the success value and returns a new Result.

        Returns:
            The Result from applying fn to the value.
        """
        return fn(self.value)

    def and_then[U, F](self, fn: Callable[[T], "Result[U, F]"]) -> "Result[U, F]":
        """Alias for bind - chain operations that return Result.

        Args:
            fn: Function that takes the success value and returns a new Result.

        Returns:
            The Result from applying fn to the value.
        """
        return fn(self.value)

    def or_else[F](self, fn: Callable[[None], "Result[T, F]"]) -> "Ok[T]":
        """Return self for Ok - no error to handle."""
        return self

    def map_err[F](self, fn: Callable) -> "Ok[T]":
        """No-op for Ok."""
        return self

    def match[U](self, on_ok: Callable[[T], U], on_err: Callable) -> U:
        """Pattern match on Result.

        Args:
            on_ok: Function to call if Ok.
            on_err: Function to call if Err (not used for Ok).

        Returns:
            Result of on_ok(value).
        """
        return on_ok(self.value)

    def flatten[U, E2](self: "Ok[Result[U, E2]]") -> "Result[U, E2]":
        """Flatten nested Result[Result[U, E], E] to Result[U, E]."""
        return self.value

    def inspect(self, fn: Callable[[T], None]) -> "Ok[T]":
        """Call function with value for side effects, return self."""
        fn(self.value)
        return self

    def inspect_err(self, fn: Callable) -> "Ok[T]":
        """No-op for Ok."""
        return self


@dataclass(frozen=True, slots=True)
class Err[E]:
    """Represents a failed result.

    Type Parameters:
        E: The type of the error value.

    **Feature: ultimate-generics-code-review-2025**
    **Validates: Requirements 5.1, 15.1**
    """

    error: E

    def is_ok(self) -> bool:
        """Check if result is Ok."""
        return False

    def to_dict(self) -> dict[str, Any]:
        """Serialize Err to dictionary for round-trip testing.

        **Feature: ultimate-generics-code-review-2025, Property 2: Result Pattern Round-Trip**
        **Validates: Requirements 15.1**

        Returns:
            Dictionary with type discriminator and error.
        """
        return {"type": "Err", "error": self.error}

    def is_err(self) -> bool:
        """Check if result is Err."""
        return True

    def unwrap(self) -> None:
        """Raises the error."""
        raise ValueError(f"Called unwrap on Err: {self.error}")

    def unwrap_or[T](self, default: T) -> T:
        """Return the default value."""
        return default

    def unwrap_or_else[T](self, fn: Callable[[E], T]) -> T:
        """Compute default from function with error."""
        return fn(self.error)

    def expect(self, msg: str) -> None:
        """Raise with custom message."""
        raise ValueError(f"{msg}: {self.error}")

    def map[U](self, fn: Callable) -> "Err[E]":
        """No-op for Err."""
        return self

    def bind[U, F](self, fn: Callable) -> "Err[E]":
        """No-op for Err - propagate the error."""
        return self

    def and_then[U, F](self, fn: Callable) -> "Err[E]":
        """No-op for Err - propagate the error."""
        return self

    def or_else[T, F](self, fn: Callable[[E], "Result[T, F]"]) -> "Result[T, F]":
        """Handle error by calling fn with error value.

        Args:
            fn: Function that takes error and returns new Result.

        Returns:
            Result from applying fn to error.
        """
        return fn(self.error)

    def map_err[U](self, fn: Callable[[E], U]) -> "Err[U]":
        """Apply function to error."""
        return Err(fn(self.error))

    def match[U](self, on_ok: Callable, on_err: Callable[[E], U]) -> U:
        """Pattern match on Result.

        Args:
            on_ok: Function to call if Ok (not used for Err).
            on_err: Function to call if Err.

        Returns:
            Result of on_err(error).
        """
        return on_err(self.error)

    def flatten(self) -> "Err[E]":
        """No-op for Err."""
        return self

    def inspect(self, fn: Callable) -> "Err[E]":
        """No-op for Err."""
        return self

    def inspect_err(self, fn: Callable[[E], None]) -> "Err[E]":
        """Call function with error for side effects, return self."""
        fn(self.error)
        return self


# Type alias for Result using PEP 695
type Result[T, E] = Ok[T] | Err[E]


def ok[T](value: T) -> Ok[T]:
    """Create an Ok result."""
    return Ok(value)


def err[E](error: E) -> Err[E]:
    """Create an Err result."""
    return Err(error)


def try_catch[T, E: Exception](
    fn: Callable[[], T],
    exception_type: type[E] = Exception,  # type: ignore
) -> Result[T, E]:
    """Execute function and catch exceptions as Err.

    Args:
        fn: Function to execute.
        exception_type: Exception type to catch.

    Returns:
        Ok with result or Err with caught exception.
    """
    try:
        return Ok(fn())
    except exception_type as e:
        return Err(e)  # type: ignore


async def try_catch_async[T, E: Exception](
    fn: Callable[[], T],
    exception_type: type[E] = Exception,  # type: ignore
) -> Result[T, E]:
    """Execute async function and catch exceptions as Err.

    Args:
        fn: Async function to execute.
        exception_type: Exception type to catch.

    Returns:
        Ok with result or Err with caught exception.
    """
    try:
        result = fn()
        if hasattr(result, "__await__"):
            result = await result
        return Ok(result)
    except exception_type as e:
        return Err(e)  # type: ignore


def collect_results[T, E](results: list[Result[T, E]]) -> Result[list[T], E]:
    """Collect list of Results into Result of list.

    Returns first Err encountered, or Ok with all values.

    **Feature: ultimate-generics-code-review-2025, Property 15: Collect Results Aggregation**
    **Validates: Requirements 5.4**

    Args:
        results: List of Result values.

    Returns:
        Ok with list of values or first Err.
    """
    values: list[T] = []
    for result in results:
        if result.is_err():
            return result  # type: ignore
        values.append(result.unwrap())
    return Ok(values)


def result_from_dict[T, E](data: dict[str, Any]) -> Result[T, E]:
    """Deserialize Result from dictionary.

    **Feature: ultimate-generics-code-review-2025, Property 2: Result Pattern Round-Trip**
    **Validates: Requirements 15.1**

    Args:
        data: Dictionary with 'type' and 'value' or 'error' keys.

    Returns:
        Ok or Err based on type discriminator.

    Raises:
        ValueError: If dictionary format is invalid.
    """
    if "type" not in data:
        raise ValueError("Missing 'type' key in Result dictionary")

    result_type = data["type"]
    if result_type == "Ok":
        if "value" not in data:
            raise ValueError("Missing 'value' key for Ok Result")
        return Ok(data["value"])
    if result_type == "Err":
        if "error" not in data:
            raise ValueError("Missing 'error' key for Err Result")
        return Err(data["error"])
    raise ValueError(f"Invalid Result type: {result_type}")
