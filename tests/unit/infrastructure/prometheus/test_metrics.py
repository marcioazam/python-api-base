"""Tests for Prometheus metrics decorators module.

Tests for counter, gauge, histogram, summary, and count_exceptions decorators.
"""

import pytest
from prometheus_client import CollectorRegistry

from infrastructure.prometheus.config import PrometheusConfig
from infrastructure.prometheus.metrics import (
    count_exceptions,
    counter,
    gauge,
    histogram,
    summary,
    timer,
)
from infrastructure.prometheus.registry import MetricsRegistry, set_registry


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    """Reset registry before each test to avoid metric conflicts."""
    registry = CollectorRegistry()
    metrics = MetricsRegistry(registry=registry)
    set_registry(metrics)


class TestCounterDecorator:
    """Tests for counter decorator."""

    def test_sync_function_increments_counter(self) -> None:
        """Counter should increment on sync function call."""

        @counter("test_sync_counter", "Test counter")
        def my_func() -> str:
            return "result"

        result = my_func()
        assert result == "result"

    @pytest.mark.asyncio
    async def test_async_function_increments_counter(self) -> None:
        """Counter should increment on async function call."""

        @counter("test_async_counter", "Test counter")
        async def my_func() -> str:
            return "async result"

        result = await my_func()
        assert result == "async result"

    def test_counter_with_labels(self) -> None:
        """Counter should work with labels."""

        @counter(
            "test_labeled_counter",
            "Test counter",
            labels=["method"],
            label_values={"method": "GET"},
        )
        def my_func() -> str:
            return "result"

        result = my_func()
        assert result == "result"

    def test_preserves_function_name(self) -> None:
        """Decorator should preserve function name."""

        @counter("test_name_counter", "Test")
        def my_named_func() -> None:
            pass

        assert my_named_func.__name__ == "my_named_func"


class TestGaugeDecorator:
    """Tests for gauge decorator."""

    def test_sync_function_tracks_inprogress(self) -> None:
        """Gauge should track in-progress calls."""

        @gauge("test_sync_gauge", "Test gauge")
        def my_func() -> str:
            return "result"

        result = my_func()
        assert result == "result"

    @pytest.mark.asyncio
    async def test_async_function_tracks_inprogress(self) -> None:
        """Gauge should track in-progress async calls."""

        @gauge("test_async_gauge", "Test gauge")
        async def my_func() -> str:
            return "async result"

        result = await my_func()
        assert result == "async result"

    def test_gauge_with_labels(self) -> None:
        """Gauge should work with labels."""

        @gauge(
            "test_labeled_gauge",
            "Test gauge",
            labels=["endpoint"],
            label_values={"endpoint": "/api"},
        )
        def my_func() -> str:
            return "result"

        result = my_func()
        assert result == "result"

    def test_gauge_no_track_inprogress(self) -> None:
        """Gauge should work without tracking in-progress."""

        @gauge("test_no_track_gauge", "Test gauge", track_inprogress=False)
        def my_func() -> str:
            return "result"

        result = my_func()
        assert result == "result"


class TestHistogramDecorator:
    """Tests for histogram decorator."""

    def test_sync_function_records_duration(self) -> None:
        """Histogram should record sync function duration."""

        @histogram("test_sync_histogram", "Test histogram")
        def my_func() -> str:
            return "result"

        result = my_func()
        assert result == "result"

    @pytest.mark.asyncio
    async def test_async_function_records_duration(self) -> None:
        """Histogram should record async function duration."""

        @histogram("test_async_histogram", "Test histogram")
        async def my_func() -> str:
            return "async result"

        result = await my_func()
        assert result == "async result"

    def test_histogram_with_labels(self) -> None:
        """Histogram should work with labels."""

        @histogram(
            "test_labeled_histogram",
            "Test histogram",
            labels=["status"],
            label_values={"status": "200"},
        )
        def my_func() -> str:
            return "result"

        result = my_func()
        assert result == "result"

    def test_histogram_with_custom_buckets(self) -> None:
        """Histogram should work with custom buckets."""

        @histogram(
            "test_buckets_histogram",
            "Test histogram",
            buckets=(0.1, 0.5, 1.0),
        )
        def my_func() -> str:
            return "result"

        result = my_func()
        assert result == "result"


class TestSummaryDecorator:
    """Tests for summary decorator."""

    def test_sync_function_records_duration(self) -> None:
        """Summary should record sync function duration."""

        @summary("test_sync_summary", "Test summary")
        def my_func() -> str:
            return "result"

        result = my_func()
        assert result == "result"

    @pytest.mark.asyncio
    async def test_async_function_records_duration(self) -> None:
        """Summary should record async function duration."""

        @summary("test_async_summary", "Test summary")
        async def my_func() -> str:
            return "async result"

        result = await my_func()
        assert result == "async result"

    def test_summary_with_labels(self) -> None:
        """Summary should work with labels."""

        @summary(
            "test_labeled_summary",
            "Test summary",
            labels=["method"],
            label_values={"method": "POST"},
        )
        def my_func() -> str:
            return "result"

        result = my_func()
        assert result == "result"


class TestTimerAlias:
    """Tests for timer alias."""

    def test_timer_is_histogram(self) -> None:
        """timer should be an alias for histogram."""
        assert timer is histogram


class TestCountExceptionsDecorator:
    """Tests for count_exceptions decorator."""

    def test_sync_function_counts_exception(self) -> None:
        """count_exceptions should count sync function exceptions."""

        @count_exceptions("test_sync_exceptions", "Test exceptions")
        def my_func() -> None:
            raise ValueError("test error")

        with pytest.raises(ValueError):
            my_func()

    @pytest.mark.asyncio
    async def test_async_function_counts_exception(self) -> None:
        """count_exceptions should count async function exceptions."""

        @count_exceptions("test_async_exceptions", "Test exceptions")
        async def my_func() -> None:
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await my_func()

    def test_no_exception_no_count(self) -> None:
        """count_exceptions should not count when no exception."""

        @count_exceptions("test_no_exception", "Test exceptions")
        def my_func() -> str:
            return "success"

        result = my_func()
        assert result == "success"

    def test_specific_exception_type(self) -> None:
        """count_exceptions should only count specific exception type."""

        @count_exceptions(
            "test_specific_exception",
            "Test exceptions",
            exception_type=ValueError,
        )
        def my_func() -> None:
            raise ValueError("test")

        with pytest.raises(ValueError):
            my_func()

    def test_with_labels(self) -> None:
        """count_exceptions should work with labels."""

        @count_exceptions(
            "test_labeled_exceptions",
            "Test exceptions",
            labels=["endpoint"],
            label_values={"endpoint": "/api"},
        )
        def my_func() -> None:
            raise RuntimeError("test")

        with pytest.raises(RuntimeError):
            my_func()
