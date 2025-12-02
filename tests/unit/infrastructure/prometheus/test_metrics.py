"""Unit tests for Prometheus metrics decorators.

**Feature: observability-infrastructure**
**Requirement: R5 - Prometheus Metrics**
"""

import pytest
import asyncio
from prometheus_client import CollectorRegistry

from infrastructure.prometheus.config import PrometheusConfig
from infrastructure.prometheus.registry import MetricsRegistry, set_registry
from infrastructure.prometheus.metrics import (
    counter,
    gauge,
    histogram,
    summary,
    timer,
    count_exceptions,
)


@pytest.fixture(autouse=True)
def setup_registry():
    """Setup fresh registry for each test."""
    test_registry = CollectorRegistry()
    config = PrometheusConfig(namespace="test")
    registry = MetricsRegistry(config, test_registry)
    set_registry(registry)
    yield registry


class TestCounterDecorator:
    """Tests for counter decorator."""

    def test_sync_counter(self, setup_registry) -> None:
        """Test counter with sync function."""

        @counter("sync_calls", "Sync function calls")
        def sync_func():
            return "done"

        result = sync_func()

        assert result == "done"

    @pytest.mark.asyncio
    async def test_async_counter(self, setup_registry) -> None:
        """Test counter with async function."""

        @counter("async_calls", "Async function calls")
        async def async_func():
            return "done"

        result = await async_func()

        assert result == "done"


class TestGaugeDecorator:
    """Tests for gauge decorator."""

    def test_sync_gauge_inprogress(self, setup_registry) -> None:
        """Test gauge tracks in-progress calls."""

        @gauge("sync_active", "Active sync calls")
        def sync_func():
            return "done"

        result = sync_func()
        assert result == "done"

    @pytest.mark.asyncio
    async def test_async_gauge_inprogress(self, setup_registry) -> None:
        """Test gauge tracks async in-progress calls."""

        @gauge("async_active", "Active async calls")
        async def async_func():
            await asyncio.sleep(0.01)
            return "done"

        result = await async_func()
        assert result == "done"


class TestHistogramDecorator:
    """Tests for histogram decorator."""

    def test_sync_histogram(self, setup_registry) -> None:
        """Test histogram with sync function."""

        @histogram("sync_duration", "Sync function duration")
        def sync_func():
            return "done"

        result = sync_func()
        assert result == "done"

    @pytest.mark.asyncio
    async def test_async_histogram(self, setup_registry) -> None:
        """Test histogram with async function."""

        @histogram("async_duration", "Async function duration")
        async def async_func():
            await asyncio.sleep(0.01)
            return "done"

        result = await async_func()
        assert result == "done"


class TestSummaryDecorator:
    """Tests for summary decorator."""

    def test_sync_summary(self, setup_registry) -> None:
        """Test summary with sync function."""

        @summary("sync_summary", "Sync function summary")
        def sync_func():
            return "done"

        result = sync_func()
        assert result == "done"


class TestTimerAlias:
    """Tests for timer alias."""

    def test_timer_is_histogram(self) -> None:
        """Test that timer is histogram."""
        assert timer is histogram


class TestCountExceptionsDecorator:
    """Tests for count_exceptions decorator."""

    def test_sync_exception_counted(self, setup_registry) -> None:
        """Test exception counting with sync function."""

        @count_exceptions("sync_errors", "Sync errors")
        def sync_func():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            sync_func()

    @pytest.mark.asyncio
    async def test_async_exception_counted(self, setup_registry) -> None:
        """Test exception counting with async function."""

        @count_exceptions("async_errors", "Async errors")
        async def async_func():
            raise RuntimeError("test error")

        with pytest.raises(RuntimeError):
            await async_func()

    def test_no_exception_not_counted(self, setup_registry) -> None:
        """Test no counting when no exception."""

        @count_exceptions("no_errors", "No errors")
        def sync_func():
            return "ok"

        result = sync_func()
        assert result == "ok"
