"""Result pattern for explicit error handling.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Ok[T]:
    """Represents a successful result."""

    value: T

    def is_ok(self) -> bool:
        """Check if result is Ok."""
        return True

    def is_err(self) -> bool:
        """Check if result is Err."""
        return False

    def unwrap(self) -> T:
        """Get the value, raises if Err."""
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Get the value or return default."""
        return self.value

    def map[U](self, fn: Callable[[T], U]) -> "Ok[U]":
        """Apply function to value."""
        return Ok(fn(self.value))

    def map_err(self, fn: Callable) -> "Ok[T]":
        """No-op for Ok."""
        return self


@dataclass(frozen=True, slots=True)
class Err[E]:
    """Represents a failed result."""

    error: E

    def is_ok(self) -> bool:
        """Check if result is Ok."""
        return False

    def is_err(self) -> bool:
        """Check if result is Err."""
        return True

    def unwrap(self) -> None:
        """Raises the error."""
        raise ValueError(f"Called unwrap on Err: {self.error}")

    def unwrap_or[T](self, default: T) -> T:
        """Return the default value."""
        return default

    def map(self, fn: Callable) -> "Err[E]":
        """No-op for Err."""
        return self

    def map_err[U](self, fn: Callable[[E], U]) -> "Err[U]":
        """Apply function to error."""
        return Err(fn(self.error))


# Type alias for Result using PEP 695
type Result[T, E] = Ok[T] | Err[E]


def ok[T](value: T) -> Ok[T]:
    """Create an Ok result."""
    return Ok(value)


def err[E](error: E) -> Err[E]:
    """Create an Err result."""
    return Err(error)
