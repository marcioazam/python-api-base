"""api_composition service."""

import asyncio
from datetime import datetime, UTC
from typing import Any
from collections.abc import Awaitable, Callable
from .enums import ExecutionStrategy, CompositionStatus
from .models import CallResult, CompositionResult
from .config import APICallConfig

# Type alias for API calls
APICall = Callable[[], Awaitable[Any]]


class APIComposer[T]:
    """Composes multiple API calls with configurable execution strategy."""

    def __init__(
        self,
        strategy: ExecutionStrategy = ExecutionStrategy.PARALLEL,
        timeout: float = 60.0,
    ) -> None:
        self._strategy = strategy
        self._timeout = timeout
        self._calls: list[APICallConfig[T]] = []

    def add_call(
        self,
        name: str,
        call: APICall,
        timeout: float = 30.0,
        required: bool = True,
        fallback: T | None = None,
        retry_count: int = 0,
    ) -> "APIComposer[T]":
        """Add an API call to the composition."""
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

    async def execute(self) -> CompositionResult[T]:
        """Execute all API calls according to the strategy."""
        start_time = datetime.now(UTC)

        if self._strategy == ExecutionStrategy.PARALLEL:
            results = await self._execute_parallel()
        elif self._strategy == ExecutionStrategy.SEQUENTIAL:
            results = await self._execute_sequential()
        else:  # PARALLEL_WITH_FALLBACK
            results = await self._execute_parallel_with_fallback()

        duration = (datetime.now(UTC) - start_time).total_seconds() * 1000
        status = self._determine_status(results)

        return CompositionResult(
            status=status,
            results=results,
            total_duration_ms=duration,
        )

    async def _execute_parallel(self) -> dict[str, CallResult[T]]:
        """Execute all calls in parallel."""
        tasks = [self._execute_single(config) for config in self._calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            config.name: (
                result
                if isinstance(result, CallResult)
                else CallResult.fail(config.name, str(result))
            )
            for config, result in zip(self._calls, results)
        }

    async def _execute_sequential(self) -> dict[str, CallResult[T]]:
        """Execute all calls sequentially."""
        results: dict[str, CallResult[T]] = {}

        for config in self._calls:
            result = await self._execute_single(config)
            results[config.name] = result

            # Stop on required failure
            if config.required and not result.success:
                break

        return results

    async def _execute_parallel_with_fallback(self) -> dict[str, CallResult[T]]:
        """Execute in parallel, use fallbacks for failures."""
        results = await self._execute_parallel()

        # Apply fallbacks
        for config in self._calls:
            result = results.get(config.name)
            if result and not result.success and config.fallback is not None:
                results[config.name] = CallResult.ok(
                    config.name, config.fallback, result.duration_ms
                )

        return results

    async def _execute_single(self, config: APICallConfig[T]) -> CallResult[T]:
        """Execute a single API call with retry logic."""
        attempts = config.retry_count + 1
        last_error = ""

        for attempt in range(attempts):
            start_time = datetime.now(UTC)
            try:
                result = await asyncio.wait_for(
                    config.call(), timeout=config.timeout
                )
                duration = (datetime.now(UTC) - start_time).total_seconds() * 1000
                return CallResult.ok(config.name, result, duration)
            except asyncio.TimeoutError:
                last_error = f"Timeout after {config.timeout}s"
            except Exception as e:
                last_error = str(e)

            # Wait before retry
            if attempt < attempts - 1:
                await asyncio.sleep(config.retry_delay)

        duration = (datetime.now(UTC) - start_time).total_seconds() * 1000
        return CallResult.fail(config.name, last_error, duration)

    def _determine_status(self, results: dict[str, CallResult[T]]) -> CompositionStatus:
        """Determine the overall status of the composition."""
        if not results:
            return CompositionStatus.SUCCESS

        all_success = all(r.success for r in results.values())
        all_failed = all(not r.success for r in results.values())

        # Check if any required call failed
        required_failed = any(
            not results.get(config.name, CallResult.fail(config.name, "")).success
            for config in self._calls
            if config.required
        )

        if all_success:
            return CompositionStatus.SUCCESS
        if all_failed or required_failed:
            return CompositionStatus.FAILED
        return CompositionStatus.PARTIAL

    @property
    def call_count(self) -> int:
        """Get the number of configured calls."""
        return len(self._calls)

class AggregatedResponse[T]:
    """Aggregated response from multiple API calls."""

    def __init__(self, composition_result: CompositionResult[T]) -> None:
        self._result = composition_result

    @property
    def data(self) -> dict[str, T]:
        """Get all successful data."""
        return self._result.successful_results

    @property
    def errors(self) -> dict[str, str]:
        """Get all errors."""
        return self._result.failed_results

    @property
    def is_complete(self) -> bool:
        """Check if all calls succeeded."""
        return self._result.status == CompositionStatus.SUCCESS

    @property
    def is_partial(self) -> bool:
        """Check if some calls failed."""
        return self._result.status == CompositionStatus.PARTIAL

    def get(self, name: str, default: T | None = None) -> T | None:
        """Get data by name with optional default."""
        return self._result.get(name) or default

    def merge(self) -> dict[str, Any]:
        """Merge all successful results into a single dict."""
        merged: dict[str, Any] = {}
        for name, data in self._result.successful_results.items():
            if isinstance(data, dict):
                merged.update(data)
            else:
                merged[name] = data
        return merged

def compose_parallel(*calls: tuple[str, APICall]) -> APIComposer[Any]:
    """Create a parallel composer with the given calls."""
    composer = APIComposer[Any](strategy=ExecutionStrategy.PARALLEL)
    for name, call in calls:
        composer.add_call(name, call)
    return composer


def compose_sequential(*calls: tuple[str, APICall]) -> APIComposer[Any]:
    """Create a sequential composer with the given calls."""
    composer = APIComposer[Any](strategy=ExecutionStrategy.SEQUENTIAL)
    for name, call in calls:
        composer.add_call(name, call)
    return composer


async def aggregate(*calls: tuple[str, APICall]) -> dict[str, Any]:
    """Aggregate multiple API calls and return combined results.

    Convenience function that creates a parallel composer, executes all calls,
    and returns the aggregated response data.

    Args:
        *calls: Tuples of (name, async_callable) for each API call.

    Returns:
        Dictionary mapping call names to their results.
    """
    composer = compose_parallel(*calls)
    result = await composer.execute()
    return AggregatedResponse(result).data
