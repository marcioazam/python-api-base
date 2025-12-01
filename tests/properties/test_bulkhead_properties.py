"""Property-based tests for Bulkhead Pattern.

**Feature: api-architecture-analysis, Property 10: Bulkhead pattern**
**Validates: Requirements 6.1**
"""

import asyncio

import pytest
from hypothesis import given, settings, strategies as st

from my_app.infrastructure.resilience.bulkhead import (
    Bulkhead,
    BulkheadRejectedError,
    BulkheadRegistry,
    BulkheadState,
    BulkheadStats,
    bulkhead,
)


identifier_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz_"),
    min_size=1,
    max_size=20,
)


class TestBulkheadStats:
    """Tests for BulkheadStats."""

    @given(max_concurrent=st.integers(min_value=1, max_value=100))
    @settings(max_examples=50)
    def test_available_permits(self, max_concurrent: int):
        """available_permits should be max - current."""
        stats = BulkheadStats(
            name="test",
            max_concurrent=max_concurrent,
            current_concurrent=max_concurrent // 2,
        )
        expected = max_concurrent - max_concurrent // 2
        assert stats.available_permits == expected

    @given(max_concurrent=st.integers(min_value=1, max_value=100))
    @settings(max_examples=50)
    def test_utilization(self, max_concurrent: int):
        """utilization should be current / max."""
        current = max_concurrent // 2
        stats = BulkheadStats(
            name="test",
            max_concurrent=max_concurrent,
            current_concurrent=current,
        )
        expected = current / max_concurrent
        assert abs(stats.utilization - expected) < 0.001

    def test_success_rate_all_success(self):
        """success_rate should be 1.0 when all succeed."""
        stats = BulkheadStats(
            name="test",
            max_concurrent=10,
            current_concurrent=0,
            total_completed=100,
            total_failed=0,
        )
        assert stats.success_rate == 1.0

    def test_success_rate_half_failed(self):
        """success_rate should be 0.5 when half fail."""
        stats = BulkheadStats(
            name="test",
            max_concurrent=10,
            current_concurrent=0,
            total_completed=50,
            total_failed=50,
        )
        assert stats.success_rate == 0.5

    def test_to_dict(self):
        """to_dict should contain all fields."""
        stats = BulkheadStats(
            name="test",
            max_concurrent=10,
            current_concurrent=5,
        )
        d = stats.to_dict()
        assert d["name"] == "test"
        assert d["max_concurrent"] == 10
        assert d["current_concurrent"] == 5


class TestBulkhead:
    """Tests for Bulkhead."""

    @pytest.mark.asyncio
    async def test_acquire_and_release(self):
        """acquire and release should work correctly."""
        bulkhead = Bulkhead("test", max_concurrent=5)
        acquired = await bulkhead.acquire()
        assert acquired is True
        assert bulkhead.stats.current_concurrent == 1
        await bulkhead.release()
        assert bulkhead.stats.current_concurrent == 0

    @pytest.mark.asyncio
    async def test_state_accepting(self):
        """state should be ACCEPTING when permits available."""
        bulkhead = Bulkhead("test", max_concurrent=5)
        assert bulkhead.state == BulkheadState.ACCEPTING

    @pytest.mark.asyncio
    async def test_state_rejecting_when_full(self):
        """state should be REJECTING when no permits available."""
        bulkhead = Bulkhead("test", max_concurrent=1)
        await bulkhead.acquire()
        assert bulkhead.state == BulkheadState.REJECTING
        await bulkhead.release()

    @pytest.mark.asyncio
    async def test_acquire_context_success(self):
        """acquire_context should track success."""
        bulkhead = Bulkhead("test", max_concurrent=5)
        async with bulkhead.acquire_context():
            assert bulkhead.stats.current_concurrent == 1
        assert bulkhead.stats.current_concurrent == 0
        assert bulkhead.stats.total_completed == 1

    @pytest.mark.asyncio
    async def test_acquire_context_failure(self):
        """acquire_context should track failure."""
        bulkhead = Bulkhead("test", max_concurrent=5)
        with pytest.raises(ValueError):
            async with bulkhead.acquire_context():
                raise ValueError("Test error")
        assert bulkhead.stats.total_failed == 1

    @pytest.mark.asyncio
    async def test_execute(self):
        """execute should run function within bulkhead."""
        bulkhead = Bulkhead("test", max_concurrent=5)

        async def add(a: int, b: int) -> int:
            return a + b

        result = await bulkhead.execute(add, 2, 3)
        assert result == 5
        assert bulkhead.stats.total_completed == 1

    @pytest.mark.asyncio
    async def test_concurrent_limit(self):
        """bulkhead should limit concurrent executions."""
        bulkhead = Bulkhead("test", max_concurrent=2, max_wait_seconds=0.1)
        results: list[bool] = []

        async def slow_task():
            await asyncio.sleep(0.5)
            return True

        async def try_execute():
            try:
                return await bulkhead.execute(slow_task)
            except BulkheadRejectedError:
                return False

        tasks = [try_execute() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        accepted = sum(1 for r in results if r is True)
        assert accepted <= 2


class TestBulkheadRegistry:
    """Tests for BulkheadRegistry."""

    def test_register_and_get(self):
        """register should store bulkhead retrievable by get."""
        registry = BulkheadRegistry()
        bulkhead = registry.register("test", max_concurrent=10)
        retrieved = registry.get("test")
        assert retrieved is bulkhead

    def test_get_nonexistent_returns_none(self):
        """get should return None for nonexistent bulkhead."""
        registry = BulkheadRegistry()
        assert registry.get("nonexistent") is None

    def test_get_or_create_creates_new(self):
        """get_or_create should create new bulkhead."""
        registry = BulkheadRegistry()
        bulkhead = registry.get_or_create("test", max_concurrent=10)
        assert bulkhead is not None
        assert bulkhead.name == "test"

    def test_get_or_create_returns_existing(self):
        """get_or_create should return existing bulkhead."""
        registry = BulkheadRegistry()
        bulkhead1 = registry.get_or_create("test", max_concurrent=10)
        bulkhead2 = registry.get_or_create("test", max_concurrent=20)
        assert bulkhead1 is bulkhead2

    def test_list_names(self):
        """list_names should return all bulkhead names."""
        registry = BulkheadRegistry()
        registry.register("bulkhead1", 10)
        registry.register("bulkhead2", 20)
        names = registry.list_names()
        assert "bulkhead1" in names
        assert "bulkhead2" in names

    def test_get_all_stats(self):
        """get_all_stats should return stats for all bulkheads."""
        registry = BulkheadRegistry()
        registry.register("bulkhead1", 10)
        registry.register("bulkhead2", 20)
        stats = registry.get_all_stats()
        assert "bulkhead1" in stats
        assert "bulkhead2" in stats


class TestBulkheadDecorator:
    """Tests for bulkhead decorator."""

    @pytest.mark.asyncio
    async def test_decorator_applies_bulkhead(self):
        """decorator should apply bulkhead to function."""
        registry = BulkheadRegistry()

        @bulkhead("test", max_concurrent=5, registry=registry)
        async def my_function(x: int) -> int:
            return x * 2

        result = await my_function(5)
        assert result == 10
        b = registry.get("test")
        assert b is not None
        assert b.stats.total_completed == 1
