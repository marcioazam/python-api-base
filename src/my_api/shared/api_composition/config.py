"""api_composition configuration."""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from .enums import ExecutionStrategy

if TYPE_CHECKING:
    from .service import APICall, APIComposer


@dataclass
class APICallConfig[T]:
    """Configuration for an API call."""

    name: str
    call: "APICall[T]"
    timeout: float = 30.0  # seconds
    required: bool = True  # If True, failure fails the whole composition
    fallback: T | None = None
    retry_count: int = 0
    retry_delay: float = 1.0  # seconds

class CompositionBuilder[T]:
    """Fluent builder for API composition."""

    def __init__(self) -> None:
        self._strategy = ExecutionStrategy.PARALLEL
        self._timeout = 60.0
        self._calls: list[APICallConfig[T]] = []

    def parallel(self) -> "CompositionBuilder[T]":
        """Set parallel execution strategy."""
        self._strategy = ExecutionStrategy.PARALLEL
        return self

    def sequential(self) -> "CompositionBuilder[T]":
        """Set sequential execution strategy."""
        self._strategy = ExecutionStrategy.SEQUENTIAL
        return self

    def parallel_with_fallback(self) -> "CompositionBuilder[T]":
        """Set parallel with fallback execution strategy."""
        self._strategy = ExecutionStrategy.PARALLEL_WITH_FALLBACK
        return self

    def timeout(self, seconds: float) -> "CompositionBuilder[T]":
        """Set overall timeout."""
        self._timeout = seconds
        return self

    def add(
        self,
        name: str,
        call: "APICall[T]",
        timeout: float = 30.0,
        required: bool = True,
        fallback: T | None = None,
        retry_count: int = 0,
    ) -> "CompositionBuilder[T]":
        """Add an API call."""
        config = APICallConfig(
            name=name,
            call=call,
            timeout=timeout,
            required=required,
            fallback=fallback,
            retry_count=retry_count,
        )
        self._calls.append(config)
        return self

    def add_optional(
        self,
        name: str,
        call: "APICall[T]",
        fallback: T,
        timeout: float = 30.0,
    ) -> "CompositionBuilder[T]":
        """Add an optional API call with fallback."""
        return self.add(
            name=name,
            call=call,
            timeout=timeout,
            required=False,
            fallback=fallback,
        )

    def build(self) -> "APIComposer[T]":
        """Build the composer."""
        from .service import APIComposer
        composer = APIComposer[T](strategy=self._strategy, timeout=self._timeout)
        for config in self._calls:
            composer._calls.append(config)
        return composer
