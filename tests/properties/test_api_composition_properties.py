"""Property-based tests for API Composition Pattern.

**Feature: api-architecture-analysis**
**Validates: Requirements 4.4**
"""

import asyncio

import pytest
from hypothesis import given, settings, strategies as st

from my_api.shared.api_composition import (
    AggregatedResponse,
    APIComposer,
    CallResult,
    CompositionBuilder,
    CompositionResult,
    CompositionStatus,
    ExecutionStrategy,
    aggregate,
    compose_parallel,
    compose_sequential,
)


# Strategies
strategy_type = st.sampled_from(list(ExecutionStrategy))
status_type = st.sampled_from(list(CompositionStatus))


class TestCallResultProperties:
    """Property tests for CallResult."""

    @given(
        name=st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
        data=st.integers(),
        duration=st.floats(min_value=0, max_value=10000, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_ok_creates_successful_result(
        self, name: str, data: int, duration: float
    ) -> None:
        """Property: ok() creates a successful result."""
        result = CallResult.ok(name, data, duration)
        assert result.success is True
        assert result.data == data
        assert result.name == name
        assert result.error is None

    @given(
        name=st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
        error=st.text(min_size=1, max_size=100),
        duration=st.floats(min_value=0, max_value=10000, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_fail_creates_failed_result(
        self, name: str, error: str, duration: float
    ) -> None:
        """Property: fail() creates a failed result."""
        result = CallResult.fail(name, error, duration)
        assert result.success is False
        assert result.error == error
        assert result.name == name
        assert result.data is None


class TestCompositionResultProperties:
    """Property tests for CompositionResult."""

    @given(
        success_count=st.integers(min_value=0, max_value=5),
        failure_count=st.integers(min_value=0, max_value=5),
    )
    @settings(max_examples=50)
    def test_success_and_failure_counts(
        self, success_count: int, failure_count: int
    ) -> None:
        """Property: success_count and failure_count are accurate."""
        results: dict[str, CallResult[int]] = {}

        for i in range(success_count):
            results[f"success_{i}"] = CallResult.ok(f"success_{i}", i)

        for i in range(failure_count):
            results[f"failure_{i}"] = CallResult.fail(f"failure_{i}", "error")

        composition = CompositionResult(
            status=CompositionStatus.SUCCESS,
            results=results,
        )

        assert composition.success_count == success_count
        assert composition.failure_count == failure_count

    def test_successful_results_filters_correctly(self) -> None:
        """Property: successful_results only includes successful calls."""
        results = {
            "ok1": CallResult.ok("ok1", 1),
            "ok2": CallResult.ok("ok2", 2),
            "fail1": CallResult.fail("fail1", "error"),
        }
        composition = CompositionResult(
            status=CompositionStatus.PARTIAL,
            results=results,
        )

        successful = composition.successful_results
        assert len(successful) == 2
        assert "ok1" in successful
        assert "ok2" in successful
        assert "fail1" not in successful

    def test_failed_results_filters_correctly(self) -> None:
        """Property: failed_results only includes failed calls."""
        results = {
            "ok1": CallResult.ok("ok1", 1),
            "fail1": CallResult.fail("fail1", "error1"),
            "fail2": CallResult.fail("fail2", "error2"),
        }
        composition = CompositionResult(
            status=CompositionStatus.PARTIAL,
            results=results,
        )

        failed = composition.failed_results
        assert len(failed) == 2
        assert "fail1" in failed
        assert "fail2" in failed
        assert "ok1" not in failed

    def test_get_returns_data_for_successful_call(self) -> None:
        """Property: get() returns data for successful calls."""
        results = {
            "test": CallResult.ok("test", 42),
        }
        composition = CompositionResult(
            status=CompositionStatus.SUCCESS,
            results=results,
        )

        assert composition.get("test") == 42
        assert composition.get("nonexistent") is None



class TestAPIComposerProperties:
    """Property tests for APIComposer."""

    @pytest.mark.anyio
    async def test_parallel_executes_all_calls(self) -> None:
        """Property: Parallel strategy executes all calls."""
        execution_order: list[str] = []

        async def call1() -> int:
            execution_order.append("call1")
            return 1

        async def call2() -> int:
            execution_order.append("call2")
            return 2

        composer = APIComposer[int](strategy=ExecutionStrategy.PARALLEL)
        composer.add_call("call1", call1)
        composer.add_call("call2", call2)

        result = await composer.execute()

        assert result.success_count == 2
        assert result.get("call1") == 1
        assert result.get("call2") == 2

    @pytest.mark.anyio
    async def test_sequential_executes_in_order(self) -> None:
        """Property: Sequential strategy executes calls in order."""
        execution_order: list[str] = []

        async def call1() -> int:
            execution_order.append("call1")
            return 1

        async def call2() -> int:
            execution_order.append("call2")
            return 2

        composer = APIComposer[int](strategy=ExecutionStrategy.SEQUENTIAL)
        composer.add_call("call1", call1)
        composer.add_call("call2", call2)

        await composer.execute()

        assert execution_order == ["call1", "call2"]

    @pytest.mark.anyio
    async def test_sequential_stops_on_required_failure(self) -> None:
        """Property: Sequential stops on required call failure."""
        execution_order: list[str] = []

        async def failing_call() -> int:
            execution_order.append("failing")
            raise ValueError("Test error")

        async def second_call() -> int:
            execution_order.append("second")
            return 2

        composer = APIComposer[int](strategy=ExecutionStrategy.SEQUENTIAL)
        composer.add_call("failing", failing_call, required=True)
        composer.add_call("second", second_call)

        result = await composer.execute()

        assert result.status == CompositionStatus.FAILED
        assert "second" not in execution_order

    @pytest.mark.anyio
    async def test_fallback_used_on_failure(self) -> None:
        """Property: Fallback is used when call fails."""

        async def failing_call() -> int:
            raise ValueError("Test error")

        composer = APIComposer[int](strategy=ExecutionStrategy.PARALLEL_WITH_FALLBACK)
        composer.add_call("test", failing_call, required=False, fallback=42)

        result = await composer.execute()

        assert result.get("test") == 42

    @pytest.mark.anyio
    async def test_timeout_causes_failure(self) -> None:
        """Property: Timeout causes call to fail."""

        async def slow_call() -> int:
            await asyncio.sleep(5)
            return 1

        composer = APIComposer[int](strategy=ExecutionStrategy.PARALLEL)
        composer.add_call("slow", slow_call, timeout=0.1)

        result = await composer.execute()

        assert result.failure_count == 1
        assert "Timeout" in (result.results["slow"].error or "")

    @given(call_count=st.integers(min_value=1, max_value=5))
    @settings(max_examples=20)
    @pytest.mark.anyio
    async def test_all_calls_executed_in_parallel(self, call_count: int) -> None:
        """Property: All calls are executed in parallel mode."""
        composer = APIComposer[int](strategy=ExecutionStrategy.PARALLEL)

        for i in range(call_count):
            async def make_call(idx: int = i) -> int:
                return idx

            composer.add_call(f"call_{i}", make_call)

        result = await composer.execute()
        assert result.success_count == call_count


class TestCompositionBuilderProperties:
    """Property tests for CompositionBuilder."""

    def test_builder_fluent_interface(self) -> None:
        """Property: Builder methods return builder for chaining."""
        builder = CompositionBuilder[int]()

        async def dummy() -> int:
            return 1

        result = (
            builder
            .parallel()
            .timeout(30.0)
            .add("test", dummy)
        )

        assert result is builder

    @pytest.mark.anyio
    async def test_builder_creates_working_composer(self) -> None:
        """Property: Builder creates a working composer."""

        async def call1() -> int:
            return 1

        async def call2() -> int:
            return 2

        composer = (
            CompositionBuilder[int]()
            .parallel()
            .add("call1", call1)
            .add("call2", call2)
            .build()
        )

        result = await composer.execute()
        assert result.success_count == 2

    @pytest.mark.anyio
    async def test_add_optional_uses_fallback(self) -> None:
        """Property: add_optional uses fallback on failure."""

        async def failing() -> int:
            raise ValueError("error")

        composer = (
            CompositionBuilder[int]()
            .parallel_with_fallback()
            .add_optional("test", failing, fallback=99)
            .build()
        )

        result = await composer.execute()
        assert result.get("test") == 99


class TestAggregatedResponseProperties:
    """Property tests for AggregatedResponse."""

    def test_data_returns_successful_results(self) -> None:
        """Property: data property returns successful results."""
        results = {
            "ok": CallResult.ok("ok", 42),
            "fail": CallResult.fail("fail", "error"),
        }
        composition = CompositionResult(
            status=CompositionStatus.PARTIAL,
            results=results,
        )
        response = AggregatedResponse(composition)

        assert response.data == {"ok": 42}

    def test_errors_returns_failed_results(self) -> None:
        """Property: errors property returns failed results."""
        results = {
            "ok": CallResult.ok("ok", 42),
            "fail": CallResult.fail("fail", "test error"),
        }
        composition = CompositionResult(
            status=CompositionStatus.PARTIAL,
            results=results,
        )
        response = AggregatedResponse(composition)

        assert response.errors == {"fail": "test error"}

    def test_is_complete_when_all_succeed(self) -> None:
        """Property: is_complete is True when all calls succeed."""
        results = {
            "ok1": CallResult.ok("ok1", 1),
            "ok2": CallResult.ok("ok2", 2),
        }
        composition = CompositionResult(
            status=CompositionStatus.SUCCESS,
            results=results,
        )
        response = AggregatedResponse(composition)

        assert response.is_complete is True
        assert response.is_partial is False

    def test_merge_combines_dict_results(self) -> None:
        """Property: merge combines dict results."""
        results = {
            "user": CallResult.ok("user", {"name": "John", "age": 30}),
            "settings": CallResult.ok("settings", {"theme": "dark"}),
        }
        composition = CompositionResult(
            status=CompositionStatus.SUCCESS,
            results=results,
        )
        response = AggregatedResponse(composition)

        merged = response.merge()
        assert merged["name"] == "John"
        assert merged["age"] == 30
        assert merged["theme"] == "dark"


class TestConvenienceFunctions:
    """Property tests for convenience functions."""

    @pytest.mark.anyio
    async def test_compose_parallel_creates_parallel_composer(self) -> None:
        """Property: compose_parallel creates parallel composer."""

        async def call1() -> int:
            return 1

        async def call2() -> int:
            return 2

        composer = compose_parallel(("call1", call1), ("call2", call2))
        result = await composer.execute()

        assert result.success_count == 2

    @pytest.mark.anyio
    async def test_compose_sequential_creates_sequential_composer(self) -> None:
        """Property: compose_sequential creates sequential composer."""
        order: list[str] = []

        async def call1() -> int:
            order.append("1")
            return 1

        async def call2() -> int:
            order.append("2")
            return 2

        composer = compose_sequential(("call1", call1), ("call2", call2))
        await composer.execute()

        assert order == ["1", "2"]

    @pytest.mark.anyio
    async def test_aggregate_returns_aggregated_response(self) -> None:
        """Property: aggregate returns AggregatedResponse."""

        async def call1() -> int:
            return 1

        async def call2() -> int:
            return 2

        response = await aggregate(("call1", call1), ("call2", call2))

        assert isinstance(response, AggregatedResponse)
        assert response.get("call1") == 1
        assert response.get("call2") == 2
