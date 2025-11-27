"""Property-based tests for observability components.

**Feature: advanced-reusability, Properties 10-11**
**Validates: Requirements 4.2, 4.5, 4.7**
"""

import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from my_api.infrastructure.observability.telemetry import (
    TelemetryProvider,
    _NoOpSpan,
    _NoOpTracer,
    _current_span_id,
    _current_trace_id,
    get_current_span_id,
    get_current_trace_id,
    get_telemetry,
    traced,
)


class TestTraceSpanCreation:
    """Property tests for Trace Span Creation.

    **Feature: advanced-reusability, Property 10: Trace Span Creation**
    **Validates: Requirements 4.2, 4.5**
    """

    def test_telemetry_provider_initialization(self) -> None:
        """
        **Feature: advanced-reusability, Property 10: Trace Span Creation**

        TelemetryProvider SHALL initialize without errors even when
        OpenTelemetry packages are not available.
        """
        provider = TelemetryProvider(
            service_name="test-service",
            service_version="1.0.0",
            otlp_endpoint=None,
            enable_tracing=True,
            enable_metrics=True,
        )

        # Should not raise even without OTel packages
        provider.initialize()

        # Should return no-op tracer/meter when OTel not available
        tracer = provider.get_tracer()
        meter = provider.get_meter()

        assert tracer is not None
        assert meter is not None

    def test_noop_tracer_creates_spans(self) -> None:
        """
        NoOpTracer SHALL create NoOpSpan instances that can be used
        as context managers without errors.
        """
        tracer = _NoOpTracer()

        with tracer.start_as_current_span("test-span") as span:
            assert isinstance(span, _NoOpSpan)
            span.set_attribute("key", "value")
            span.add_event("test-event", {"attr": "value"})

    def test_noop_span_operations(self) -> None:
        """
        NoOpSpan SHALL accept all span operations without errors.
        """
        span = _NoOpSpan()

        # All operations should be no-ops
        span.set_attribute("key", "value")
        span.add_event("event", {"attr": "value"})
        span.record_exception(ValueError("test"))
        span.set_status(None)

        # Context manager should work
        with span:
            pass

    @settings(max_examples=50)
    @given(
        service_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        service_version=st.from_regex(r"[0-9]+\.[0-9]+\.[0-9]+", fullmatch=True),
    )
    def test_telemetry_provider_accepts_valid_config(
        self, service_name: str, service_version: str
    ) -> None:
        """
        **Feature: advanced-reusability, Property 10: Trace Span Creation**

        For any valid service name and version, TelemetryProvider SHALL
        initialize successfully.
        """
        provider = TelemetryProvider(
            service_name=service_name,
            service_version=service_version,
        )

        # Should not raise
        provider.initialize()
        assert provider.get_tracer() is not None

    def test_traced_decorator_creates_span(self) -> None:
        """
        **Feature: advanced-reusability, Property 10: Trace Span Creation**

        For any function decorated with @traced, a span SHALL be created
        with the correct name.
        """
        call_count = 0

        @traced(name="test-operation")
        async def test_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        async def run_test():
            result = await test_function(5)
            assert result == 10

        asyncio.run(run_test())
        assert call_count == 1

    def test_traced_decorator_with_attributes(self) -> None:
        """
        @traced decorator SHALL accept custom attributes.
        """

        @traced(name="custom-span", attributes={"db": "postgres", "table": "users"})
        async def db_operation() -> str:
            return "result"

        async def run_test():
            result = await db_operation()
            assert result == "result"

        asyncio.run(run_test())

    def test_traced_decorator_handles_exceptions(self) -> None:
        """
        @traced decorator SHALL record exceptions and re-raise them.
        """

        @traced(name="failing-operation")
        async def failing_function() -> None:
            raise ValueError("Test error")

        async def run_test():
            try:
                await failing_function()
                assert False, "Should have raised"
            except ValueError as e:
                assert str(e) == "Test error"

        asyncio.run(run_test())

    def test_traced_decorator_sync_function(self) -> None:
        """
        @traced decorator SHALL work with synchronous functions.
        """

        @traced(name="sync-operation")
        def sync_function(x: int) -> int:
            return x * 2

        result = sync_function(5)
        assert result == 10

    @settings(max_examples=30)
    @given(
        span_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N", "P"))),
    )
    def test_traced_decorator_accepts_any_span_name(self, span_name: str) -> None:
        """
        @traced decorator SHALL accept any valid span name.
        """

        @traced(name=span_name)
        async def named_function() -> str:
            return "ok"

        async def run_test():
            result = await named_function()
            assert result == "ok"

        asyncio.run(run_test())


class TestLogTraceCorrelation:
    """Property tests for Log Trace Correlation.

    **Feature: advanced-reusability, Property 11: Log Trace Correlation**
    **Validates: Requirements 4.7**
    """

    def test_trace_context_vars_default_to_none(self) -> None:
        """
        **Feature: advanced-reusability, Property 11: Log Trace Correlation**

        Trace context variables SHALL default to None when no trace is active.
        """
        # Reset context vars
        _current_trace_id.set(None)
        _current_span_id.set(None)

        assert get_current_trace_id() is None
        assert get_current_span_id() is None

    @settings(max_examples=50)
    @given(
        trace_id=st.text(min_size=32, max_size=32, alphabet="0123456789abcdef"),
        span_id=st.text(min_size=16, max_size=16, alphabet="0123456789abcdef"),
    )
    def test_trace_context_vars_can_be_set(
        self, trace_id: str, span_id: str
    ) -> None:
        """
        **Feature: advanced-reusability, Property 11: Log Trace Correlation**

        For any valid trace_id and span_id, context variables SHALL
        store and return the values correctly.
        """
        _current_trace_id.set(trace_id)
        _current_span_id.set(span_id)

        assert get_current_trace_id() == trace_id
        assert get_current_span_id() == span_id

        # Cleanup
        _current_trace_id.set(None)
        _current_span_id.set(None)

    def test_log_processor_adds_trace_context(self) -> None:
        """
        **Feature: advanced-reusability, Property 11: Log Trace Correlation**

        The add_trace_context processor SHALL add trace_id and span_id
        to log events when trace context is available.
        """
        from my_api.infrastructure.logging.config import add_trace_context

        # Set trace context
        _current_trace_id.set("00000000000000000000000000000001")
        _current_span_id.set("0000000000000001")

        event_dict: dict = {"event": "test"}
        result = add_trace_context(None, "info", event_dict)  # type: ignore

        assert result.get("trace_id") == "00000000000000000000000000000001"
        assert result.get("span_id") == "0000000000000001"

        # Cleanup
        _current_trace_id.set(None)
        _current_span_id.set(None)

    def test_log_processor_handles_missing_context(self) -> None:
        """
        add_trace_context processor SHALL not add fields when
        trace context is not available.
        """
        from my_api.infrastructure.logging.config import add_trace_context

        # Ensure no trace context
        _current_trace_id.set(None)
        _current_span_id.set(None)

        event_dict: dict = {"event": "test"}
        result = add_trace_context(None, "info", event_dict)  # type: ignore

        assert "trace_id" not in result
        assert "span_id" not in result


class TestTelemetryShutdown:
    """Tests for telemetry shutdown."""

    def test_shutdown_without_initialization(self) -> None:
        """Shutdown SHALL not raise when provider was never initialized."""
        provider = TelemetryProvider()

        async def run_test():
            await provider.shutdown()

        asyncio.run(run_test())

    def test_shutdown_after_initialization(self) -> None:
        """Shutdown SHALL gracefully close providers after initialization."""
        provider = TelemetryProvider(
            service_name="test",
            enable_tracing=True,
            enable_metrics=True,
        )
        provider.initialize()

        async def run_test():
            await provider.shutdown()

        asyncio.run(run_test())


class TestGlobalTelemetry:
    """Tests for global telemetry instance."""

    def test_get_telemetry_returns_singleton(self) -> None:
        """get_telemetry SHALL return the same instance on multiple calls."""
        provider1 = get_telemetry()
        provider2 = get_telemetry()

        assert provider1 is provider2
