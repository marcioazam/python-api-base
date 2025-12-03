"""Integration tests for Prometheus metrics collection.

**Feature: infrastructure-modules-integration-analysis**
**Validates: Requirements 4.4**
"""

import pytest
from prometheus_client import CollectorRegistry

from infrastructure.prometheus.config import PrometheusConfig
from infrastructure.prometheus.registry import MetricsRegistry, set_registry
from infrastructure.prometheus.metrics import counter, histogram


class TestMetricsCollection:
    """Integration tests for metrics collection in use cases.
    
    **Feature: infrastructure-modules-integration-analysis**
    **Validates: Requirements 4.4**
    """

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """Setup fresh registry for each test."""
        test_registry = CollectorRegistry()
        config = PrometheusConfig(namespace="test")
        registry = MetricsRegistry(config, test_registry)
        set_registry(registry)
        yield registry

    def test_counter_increments(self, setup_registry) -> None:
        """Test counter increments on function call.
        
        **Validates: Requirements 4.4**
        """
        call_count = 0

        @counter("test_operations", "Test operations count")
        def test_operation():
            nonlocal call_count
            call_count += 1
            return "done"

        # Call function multiple times
        for _ in range(5):
            result = test_operation()
            assert result == "done"

        assert call_count == 5

    @pytest.mark.asyncio
    async def test_async_counter_increments(self, setup_registry) -> None:
        """Test async counter increments on function call.
        
        **Validates: Requirements 4.4**
        """
        call_count = 0

        @counter("test_async_operations", "Test async operations count")
        async def test_async_operation():
            nonlocal call_count
            call_count += 1
            return "done"

        # Call function multiple times
        for _ in range(3):
            result = await test_async_operation()
            assert result == "done"

        assert call_count == 3

    def test_histogram_records_duration(self, setup_registry) -> None:
        """Test histogram records function duration.
        
        **Validates: Requirements 4.4**
        """
        import time

        @histogram("test_duration", "Test duration")
        def slow_operation():
            time.sleep(0.01)
            return "done"

        result = slow_operation()
        assert result == "done"

    @pytest.mark.asyncio
    async def test_async_histogram_records_duration(self, setup_registry) -> None:
        """Test async histogram records function duration.
        
        **Validates: Requirements 4.4**
        """
        import asyncio

        @histogram("test_async_duration", "Test async duration")
        async def slow_async_operation():
            await asyncio.sleep(0.01)
            return "done"

        result = await slow_async_operation()
        assert result == "done"


class TestUseCaseMetrics:
    """Tests for use case metrics patterns.
    
    **Feature: infrastructure-modules-integration-analysis**
    **Validates: Requirements 4.4**
    """

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """Setup fresh registry for each test."""
        test_registry = CollectorRegistry()
        config = PrometheusConfig(namespace="app")
        registry = MetricsRegistry(config, test_registry)
        set_registry(registry)
        yield registry

    def test_use_case_pattern(self, setup_registry) -> None:
        """Test metrics pattern for use cases.
        
        **Validates: Requirements 4.4**
        """

        class MockUseCase:
            """Mock use case with metrics."""

            @counter("item_creates", "Item create operations")
            @histogram("item_create_duration", "Item create duration")
            def create(self, data: dict) -> dict:
                return {"id": "123", **data}

            @counter("item_gets", "Item get operations")
            @histogram("item_get_duration", "Item get duration")
            def get(self, item_id: str) -> dict:
                return {"id": item_id, "name": "Test"}

        use_case = MockUseCase()

        # Test create
        result = use_case.create({"name": "Test Item"})
        assert result["id"] == "123"
        assert result["name"] == "Test Item"

        # Test get
        result = use_case.get("123")
        assert result["id"] == "123"
