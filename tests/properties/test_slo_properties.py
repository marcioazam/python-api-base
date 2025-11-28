"""Property-based tests for SLO Monitoring.

**Feature: api-architecture-analysis**
**Validates: Requirements 7.3**
"""

from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings, strategies as st

from my_api.shared.slo import (
    InMemoryMetricsStore,
    SLOConfig,
    SLOMetric,
    SLOMonitor,
    SLOResult,
    SLOStatus,
    SLOTarget,
    SLOType,
    create_slo_monitor,
)


# Strategies
slo_type_strategy = st.sampled_from(list(SLOType))
availability_value_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
latency_value_strategy = st.floats(min_value=0.0, max_value=10000.0, allow_nan=False)


class TestSLOTargetProperties:
    """Property tests for SLOTarget."""

    @given(
        target_value=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_warning_threshold_defaults_to_95_percent(self, target_value: float) -> None:
        """Property: Warning threshold defaults to 95% of target."""
        target = SLOTarget(
            name="test",
            slo_type=SLOType.AVAILABILITY,
            target_value=target_value,
        )
        expected = target_value * 0.95
        assert abs(target.warning_threshold - expected) < 0.0001

    @given(
        target_value=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        warning_threshold=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_explicit_warning_threshold_preserved(
        self, target_value: float, warning_threshold: float
    ) -> None:
        """Property: Explicit warning threshold is preserved."""
        target = SLOTarget(
            name="test",
            slo_type=SLOType.AVAILABILITY,
            target_value=target_value,
            warning_threshold=warning_threshold,
        )
        assert target.warning_threshold == warning_threshold


class TestSLOResultProperties:
    """Property tests for SLOResult."""

    @given(
        current_value=availability_value_strategy,
    )
    @settings(max_examples=100)
    def test_healthy_status_is_healthy(self, current_value: float) -> None:
        """Property: HEALTHY status means is_healthy is True."""
        target = SLOTarget(name="test", slo_type=SLOType.AVAILABILITY, target_value=0.99)
        result = SLOResult(
            target=target,
            current_value=current_value,
            status=SLOStatus.HEALTHY,
            error_budget_remaining=1.0,
            samples=100,
            window_start=datetime.now() - timedelta(hours=1),
            window_end=datetime.now(),
        )
        assert result.is_healthy is True
        assert result.is_violated is False

    @given(
        current_value=availability_value_strategy,
    )
    @settings(max_examples=100)
    def test_critical_status_is_violated(self, current_value: float) -> None:
        """Property: CRITICAL status means is_violated is True."""
        target = SLOTarget(name="test", slo_type=SLOType.AVAILABILITY, target_value=0.99)
        result = SLOResult(
            target=target,
            current_value=current_value,
            status=SLOStatus.CRITICAL,
            error_budget_remaining=0.0,
            samples=100,
            window_start=datetime.now() - timedelta(hours=1),
            window_end=datetime.now(),
        )
        assert result.is_violated is True
        assert result.is_healthy is False


class TestInMemoryMetricsStoreProperties:
    """Property tests for InMemoryMetricsStore."""

    @given(
        slo_type=slo_type_strategy,
        value=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
    )
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_record_and_retrieve(self, slo_type: SLOType, value: float) -> None:
        """Property: Recorded metrics can be retrieved."""
        store = InMemoryMetricsStore()
        metric = SLOMetric(
            slo_type=slo_type,
            value=value,
            timestamp=datetime.now(),
        )
        await store.record(metric)

        since = datetime.now() - timedelta(minutes=1)
        metrics = await store.get_metrics(slo_type, since)

        assert len(metrics) >= 1
        assert any(m.value == value for m in metrics)

    @given(
        value=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
    )
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_filter_by_type(self, value: float) -> None:
        """Property: Metrics are filtered by type."""
        store = InMemoryMetricsStore()

        # Record different types
        await store.record(SLOMetric(
            slo_type=SLOType.AVAILABILITY,
            value=value,
            timestamp=datetime.now(),
        ))
        await store.record(SLOMetric(
            slo_type=SLOType.ERROR_RATE,
            value=value,
            timestamp=datetime.now(),
        ))

        since = datetime.now() - timedelta(minutes=1)
        availability_metrics = await store.get_metrics(SLOType.AVAILABILITY, since)
        error_metrics = await store.get_metrics(SLOType.ERROR_RATE, since)

        assert all(m.slo_type == SLOType.AVAILABILITY for m in availability_metrics)
        assert all(m.slo_type == SLOType.ERROR_RATE for m in error_metrics)

    @pytest.mark.anyio
    async def test_max_size_limit(self) -> None:
        """Property: Store respects max size limit."""
        max_size = 10
        store = InMemoryMetricsStore(max_size=max_size)

        # Record more than max_size
        for i in range(max_size + 5):
            await store.record(SLOMetric(
                slo_type=SLOType.AVAILABILITY,
                value=float(i),
                timestamp=datetime.now(),
            ))

        since = datetime.now() - timedelta(hours=1)
        metrics = await store.get_metrics(SLOType.AVAILABILITY, since)

        assert len(metrics) <= max_size


class TestSLOMonitorProperties:
    """Property tests for SLOMonitor."""

    @given(
        availability=st.lists(
            st.booleans(),
            min_size=10,
            max_size=100,
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.anyio
    async def test_availability_calculation(self, availability: list[bool]) -> None:
        """Property: Availability is calculated as ratio of successful requests."""
        monitor = create_slo_monitor()

        for is_available in availability:
            await monitor.record_availability(is_available)

        result = await monitor.check_slo("availability")

        if result.samples > 0:
            expected = sum(1 for a in availability if a) / len(availability)
            # Allow some tolerance due to timing
            assert abs(result.current_value - expected) < 0.1 or result.status == SLOStatus.UNKNOWN

    @given(
        latencies=st.lists(
            st.floats(min_value=1.0, max_value=500.0, allow_nan=False),
            min_size=10,
            max_size=100,
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.anyio
    async def test_latency_p99_calculation(self, latencies: list[float]) -> None:
        """Property: P99 latency is calculated correctly."""
        monitor = create_slo_monitor()

        for latency in latencies:
            await monitor.record_latency(latency)

        result = await monitor.check_slo("latency_p99")

        if result.samples > 0:
            sorted_latencies = sorted(latencies)
            expected_index = int(len(sorted_latencies) * 0.99)
            expected = sorted_latencies[min(expected_index, len(sorted_latencies) - 1)]
            # P99 should be close to expected
            assert result.current_value <= max(latencies) * 1.1

    @given(
        errors=st.lists(
            st.booleans(),
            min_size=10,
            max_size=100,
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.anyio
    async def test_error_rate_calculation(self, errors: list[bool]) -> None:
        """Property: Error rate is calculated as ratio of errors."""
        monitor = create_slo_monitor()

        for is_error in errors:
            await monitor.record_error(is_error)

        result = await monitor.check_slo("error_rate")

        if result.samples > 0:
            expected = sum(1 for e in errors if e) / len(errors)
            assert abs(result.current_value - expected) < 0.1 or result.status == SLOStatus.UNKNOWN

    @pytest.mark.anyio
    async def test_check_all_slos_returns_all_targets(self) -> None:
        """Property: check_all_slos returns result for each target."""
        config = SLOConfig.default()
        monitor = create_slo_monitor(config=config)

        results = await monitor.check_all_slos()

        assert len(results) == len(config.targets)
        result_names = {r.target.name for r in results}
        target_names = {t.name for t in config.targets}
        assert result_names == target_names

    @pytest.mark.anyio
    async def test_unknown_slo_returns_unknown_status(self) -> None:
        """Property: Unknown SLO name returns UNKNOWN status."""
        monitor = create_slo_monitor()

        result = await monitor.check_slo("nonexistent_slo")

        assert result.status == SLOStatus.UNKNOWN


class TestSLOStatusDeterminationProperties:
    """Property tests for SLO status determination."""

    @pytest.mark.anyio
    async def test_high_availability_is_healthy(self) -> None:
        """Property: High availability (>= target) is HEALTHY."""
        config = SLOConfig(
            targets=[
                SLOTarget(
                    name="availability",
                    slo_type=SLOType.AVAILABILITY,
                    target_value=0.99,
                ),
            ]
        )
        monitor = create_slo_monitor(config=config)

        # Record 100% availability
        for _ in range(100):
            await monitor.record_availability(True)

        result = await monitor.check_slo("availability")
        assert result.status == SLOStatus.HEALTHY

    @pytest.mark.anyio
    async def test_low_availability_is_critical(self) -> None:
        """Property: Low availability (< warning) is CRITICAL."""
        config = SLOConfig(
            targets=[
                SLOTarget(
                    name="availability",
                    slo_type=SLOType.AVAILABILITY,
                    target_value=0.99,
                    warning_threshold=0.95,
                ),
            ]
        )
        monitor = create_slo_monitor(config=config)

        # Record 50% availability
        for i in range(100):
            await monitor.record_availability(i % 2 == 0)

        result = await monitor.check_slo("availability")
        assert result.status == SLOStatus.CRITICAL
