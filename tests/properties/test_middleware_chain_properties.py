"""Property-based tests for Generic Middleware Chain.

**Feature: api-architecture-analysis**
**Validates: Requirements 4.4**
"""

import pytest
from hypothesis import given, settings, strategies as st

from my_api.shared.middleware_chain import (
    ErrorHandlerMiddleware,
    FunctionMiddleware,
    LoggingMiddleware,
    Middleware,
    MiddlewareChain,
    MiddlewareChainBuilder,
    MiddlewareContext,
    MiddlewarePriority,
    NextHandler,
    create_middleware_chain,
)


# Test middleware implementations
class CounterMiddleware(Middleware[dict]):
    """Middleware that increments a counter."""

    def __init__(self, name: str, increment: int = 1) -> None:
        super().__init__(name)
        self.increment = increment

    async def process(
        self,
        context: MiddlewareContext[dict],
        next_handler: NextHandler,
    ) -> MiddlewareContext[dict]:
        context.data["counter"] = context.data.get("counter", 0) + self.increment
        context.metadata[f"{self.name}_before"] = True
        result = await next_handler(context)
        context.metadata[f"{self.name}_after"] = True
        return result


class StopMiddleware(Middleware[dict]):
    """Middleware that stops the chain."""

    async def process(
        self,
        context: MiddlewareContext[dict],
        next_handler: NextHandler,
    ) -> MiddlewareContext[dict]:
        context.stop()
        return context


class TestMiddlewareContextProperties:
    """Property tests for MiddlewareContext."""

    @given(data=st.dictionaries(st.text(min_size=1, max_size=10), st.integers()))
    @settings(max_examples=100)
    def test_context_preserves_data(self, data: dict) -> None:
        """Property: Context preserves data."""
        context = MiddlewareContext(data=data)
        assert context.data == data

    def test_stop_sets_should_continue_false(self) -> None:
        """Property: stop() sets should_continue to False."""
        context = MiddlewareContext(data={})
        assert context.should_continue is True
        context.stop()
        assert context.should_continue is False

    def test_set_error_stops_and_sets_error(self) -> None:
        """Property: set_error stops chain and sets error."""
        context = MiddlewareContext(data={})
        error = ValueError("test error")
        context.set_error(error)
        assert context.should_continue is False
        assert context.error is error


class TestMiddlewareChainProperties:
    """Property tests for MiddlewareChain."""

    @pytest.mark.anyio
    async def test_empty_chain_returns_context(self) -> None:
        """Property: Empty chain returns context unchanged."""
        chain = create_middleware_chain()
        context = MiddlewareContext(data={"value": 42})

        result = await chain.execute(context)

        assert result.data["value"] == 42

    @pytest.mark.anyio
    async def test_middlewares_execute_in_order(self) -> None:
        """Property: Middlewares execute in priority order."""
        chain = MiddlewareChain[dict]()
        chain.add(CounterMiddleware("first", increment=1))
        chain.add(CounterMiddleware("second", increment=10))
        chain.add(CounterMiddleware("third", increment=100))

        context = MiddlewareContext(data={"counter": 0})
        result = await chain.execute(context)

        # All middlewares should have executed
        assert result.data["counter"] == 111

    @pytest.mark.anyio
    async def test_priority_ordering(self) -> None:
        """Property: Higher priority middlewares execute first."""
        chain = MiddlewareChain[dict]()

        # Add in reverse priority order
        low = CounterMiddleware("low", increment=1)
        low.priority = MiddlewarePriority.LOW

        high = CounterMiddleware("high", increment=10)
        high.priority = MiddlewarePriority.HIGH

        chain.add(low)
        chain.add(high)

        # High priority should be first in sorted list
        assert chain.middlewares[0].name == "high"
        assert chain.middlewares[1].name == "low"


    @pytest.mark.anyio
    async def test_stop_prevents_further_execution(self) -> None:
        """Property: Stopping chain prevents further middleware execution."""
        chain = MiddlewareChain[dict]()
        chain.add(CounterMiddleware("first", increment=1))
        chain.add(StopMiddleware("stopper"))
        chain.add(CounterMiddleware("third", increment=100))

        context = MiddlewareContext(data={"counter": 0})
        result = await chain.execute(context)

        # Only first middleware should have executed
        assert result.data["counter"] == 1
        assert result.should_continue is False

    @pytest.mark.anyio
    async def test_disabled_middleware_skipped(self) -> None:
        """Property: Disabled middleware is skipped."""
        chain = MiddlewareChain[dict]()
        m1 = CounterMiddleware("first", increment=1)
        m2 = CounterMiddleware("second", increment=10)
        m2.enabled = False
        m3 = CounterMiddleware("third", increment=100)

        chain.add(m1)
        chain.add(m2)
        chain.add(m3)

        context = MiddlewareContext(data={"counter": 0})
        result = await chain.execute(context)

        # Second middleware should be skipped
        assert result.data["counter"] == 101

    @given(count=st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    @pytest.mark.anyio
    async def test_chain_length_matches_added(self, count: int) -> None:
        """Property: Chain length matches number of added middlewares."""
        chain = MiddlewareChain[dict]()

        for i in range(count):
            chain.add(CounterMiddleware(f"middleware_{i}"))

        assert len(chain) == count

    @pytest.mark.anyio
    async def test_remove_middleware(self) -> None:
        """Property: Removed middleware is not executed."""
        chain = MiddlewareChain[dict]()
        chain.add(CounterMiddleware("first", increment=1))
        chain.add(CounterMiddleware("second", increment=10))
        chain.add(CounterMiddleware("third", increment=100))

        chain.remove("second")

        context = MiddlewareContext(data={"counter": 0})
        result = await chain.execute(context)

        assert result.data["counter"] == 101
        assert len(chain) == 2

    @pytest.mark.anyio
    async def test_enable_disable_middleware(self) -> None:
        """Property: Enable/disable toggles middleware execution."""
        chain = MiddlewareChain[dict]()
        chain.add(CounterMiddleware("test", increment=10))

        # Disable
        chain.disable("test")
        context = MiddlewareContext(data={"counter": 0})
        result = await chain.execute(context)
        assert result.data["counter"] == 0

        # Enable
        chain.enable("test")
        context = MiddlewareContext(data={"counter": 0})
        result = await chain.execute(context)
        assert result.data["counter"] == 10


class TestFunctionMiddlewareProperties:
    """Property tests for FunctionMiddleware."""

    @pytest.mark.anyio
    async def test_function_middleware_executes(self) -> None:
        """Property: Function middleware executes correctly."""
        async def my_middleware(
            context: MiddlewareContext[dict],
            next_handler: NextHandler,
        ) -> MiddlewareContext[dict]:
            context.data["processed"] = True
            return await next_handler(context)

        chain = MiddlewareChain[dict]()
        chain.add_function(my_middleware, "my_middleware")

        context = MiddlewareContext(data={})
        result = await chain.execute(context)

        assert result.data["processed"] is True


class TestMiddlewareChainBuilderProperties:
    """Property tests for MiddlewareChainBuilder."""

    @pytest.mark.anyio
    async def test_builder_creates_working_chain(self) -> None:
        """Property: Builder creates a working chain."""
        chain = (
            MiddlewareChainBuilder[dict]()
            .use(CounterMiddleware("first", increment=1))
            .use(CounterMiddleware("second", increment=10))
            .build()
        )

        context = MiddlewareContext(data={"counter": 0})
        result = await chain.execute(context)

        assert result.data["counter"] == 11


class TestErrorHandlerMiddlewareProperties:
    """Property tests for ErrorHandlerMiddleware."""

    @pytest.mark.anyio
    async def test_error_handler_catches_errors(self) -> None:
        """Property: Error handler catches and handles errors."""
        errors_caught: list[Exception] = []

        def handler(e: Exception) -> None:
            errors_caught.append(e)

        class ErrorMiddleware(Middleware[dict]):
            async def process(
                self,
                context: MiddlewareContext[dict],
                next_handler: NextHandler,
            ) -> MiddlewareContext[dict]:
                raise ValueError("test error")

        chain = MiddlewareChain[dict]()
        chain.add(ErrorHandlerMiddleware(error_handler=handler))
        chain.add(ErrorMiddleware("error"))

        context = MiddlewareContext(data={})
        result = await chain.execute(context)

        assert len(errors_caught) == 1
        assert isinstance(errors_caught[0], ValueError)
        assert result.error is not None


class TestLoggingMiddlewareProperties:
    """Property tests for LoggingMiddleware."""

    @pytest.mark.anyio
    async def test_logging_middleware_passes_through(self) -> None:
        """Property: Logging middleware passes context through."""
        chain = MiddlewareChain[dict]()
        chain.add(LoggingMiddleware())
        chain.add(CounterMiddleware("counter", increment=5))

        context = MiddlewareContext(data={"counter": 0})
        result = await chain.execute(context)

        assert result.data["counter"] == 5
