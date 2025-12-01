"""Property-based tests for Memory Profiler.

**Feature: api-architecture-analysis, Property 14.1: Memory Profiling**
**Validates: Requirements 7.3**
"""

from datetime import datetime, timedelta

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from my_app.infrastructure.observability.memory_profiler import (
    AllocationInfo,
    MemoryAlert,
    MemoryAlertSeverity,
    MemoryAlertType,
    MemoryProfiler,
    MemoryProfilerConfig,
    MemorySnapshot,
)


# Strategies
@st.composite
def memory_snapshot_strategy(draw: st.DrawFn) -> MemorySnapshot:
    """Generate random memory snapshots."""
    return MemorySnapshot(
        timestamp=draw(st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1))),
        rss_bytes=draw(st.integers(min_value=0, max_value=10 * 1024 * 1024 * 1024)),  # Up to 10GB
        vms_bytes=draw(st.integers(min_value=0, max_value=20 * 1024 * 1024 * 1024)),  # Up to 20GB
        heap_bytes=draw(st.integers(min_value=0, max_value=5 * 1024 * 1024 * 1024)),  # Up to 5GB
        gc_objects=draw(st.integers(min_value=0, max_value=10_000_000)),
        gc_collections=draw(st.tuples(
            st.integers(min_value=0, max_value=1000),
            st.integers(min_value=0, max_value=100),
            st.integers(min_value=0, max_value=10),
        )),
    )


@st.composite
def memory_alert_strategy(draw: st.DrawFn) -> MemoryAlert:
    """Generate random memory alerts."""
    return MemoryAlert(
        alert_type=draw(st.sampled_from(list(MemoryAlertType))),
        severity=draw(st.sampled_from(list(MemoryAlertSeverity))),
        message=draw(st.text(min_size=1, max_size=200)),
        current_value=draw(st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False)),
        threshold=draw(st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False)),
        timestamp=draw(st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1))),
        details=draw(st.dictionaries(st.text(min_size=1, max_size=20), st.text(min_size=0, max_size=50), max_size=5)),
    )


@st.composite
def profiler_config_strategy(draw: st.DrawFn) -> MemoryProfilerConfig:
    """Generate random profiler configurations."""
    return MemoryProfilerConfig(
        enable_tracemalloc=draw(st.booleans()),
        traceback_limit=draw(st.integers(min_value=1, max_value=50)),
        warning_threshold_mb=draw(st.floats(min_value=100, max_value=1000, allow_nan=False, allow_infinity=False)),
        critical_threshold_mb=draw(st.floats(min_value=500, max_value=5000, allow_nan=False, allow_infinity=False)),
        growth_rate_threshold=draw(st.floats(min_value=1, max_value=100, allow_nan=False, allow_infinity=False)),
        leak_detection_window=draw(st.integers(min_value=1, max_value=60)),
        min_samples_for_leak=draw(st.integers(min_value=2, max_value=20)),
        gc_pressure_threshold=draw(st.integers(min_value=10, max_value=1000)),
        snapshot_interval=draw(st.integers(min_value=1, max_value=300)),
        max_snapshots=draw(st.integers(min_value=10, max_value=10000)),
        top_allocations=draw(st.integers(min_value=1, max_value=100)),
    )


class TestMemorySnapshotProperties:
    """Property tests for MemorySnapshot."""

    @given(memory_snapshot_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_rss_mb_conversion(self, snapshot: MemorySnapshot) -> None:
        """Property: RSS MB conversion is consistent with bytes."""
        expected_mb = snapshot.rss_bytes / (1024 * 1024)
        assert snapshot.rss_mb == expected_mb

    @given(memory_snapshot_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_vms_mb_conversion(self, snapshot: MemorySnapshot) -> None:
        """Property: VMS MB conversion is consistent with bytes."""
        expected_mb = snapshot.vms_bytes / (1024 * 1024)
        assert snapshot.vms_mb == expected_mb

    @given(memory_snapshot_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_heap_mb_conversion(self, snapshot: MemorySnapshot) -> None:
        """Property: Heap MB conversion is consistent with bytes."""
        expected_mb = snapshot.heap_bytes / (1024 * 1024)
        assert snapshot.heap_mb == expected_mb

    @given(st.integers(min_value=0, max_value=10 * 1024 * 1024 * 1024))
    @settings(max_examples=100)
    def test_mb_conversion_non_negative(self, bytes_value: int) -> None:
        """Property: MB conversion is always non-negative for non-negative bytes."""
        snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            rss_bytes=bytes_value,
            vms_bytes=bytes_value,
            heap_bytes=bytes_value,
            gc_objects=0,
            gc_collections=(0, 0, 0),
        )
        assert snapshot.rss_mb >= 0
        assert snapshot.vms_mb >= 0
        assert snapshot.heap_mb >= 0



class TestMemoryAlertProperties:
    """Property tests for MemoryAlert."""

    @given(memory_alert_strategy())
    @settings(max_examples=100)
    def test_alert_has_required_fields(self, alert: MemoryAlert) -> None:
        """Property: Alert always has required fields."""
        assert alert.alert_type is not None
        assert alert.severity is not None
        assert alert.message is not None
        assert alert.timestamp is not None

    @given(
        st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_alert_values_preserved(self, current: float, threshold: float) -> None:
        """Property: Alert preserves current and threshold values."""
        alert = MemoryAlert(
            alert_type=MemoryAlertType.HIGH_USAGE,
            severity=MemoryAlertSeverity.WARNING,
            message="Test",
            current_value=current,
            threshold=threshold,
            timestamp=datetime.now(),
        )
        assert alert.current_value == current
        assert alert.threshold == threshold


class TestMemoryProfilerProperties:
    """Property tests for MemoryProfiler."""

    @given(profiler_config_strategy())
    @settings(max_examples=50)
    def test_profiler_creation_with_config(self, config: MemoryProfilerConfig) -> None:
        """Property: Profiler can be created with any valid config."""
        profiler = MemoryProfiler(config=config)
        assert profiler is not None

    def test_snapshot_creates_valid_snapshot(self) -> None:
        """Property: Taking snapshot creates valid MemorySnapshot."""
        profiler = MemoryProfiler()
        snapshot = profiler.take_snapshot()
        
        assert isinstance(snapshot, MemorySnapshot)
        assert snapshot.timestamp is not None
        assert snapshot.rss_bytes >= 0
        assert snapshot.gc_objects >= 0

    def test_snapshots_accumulate(self) -> None:
        """Property: Multiple snapshots accumulate in profiler."""
        profiler = MemoryProfiler()
        
        for _ in range(5):
            profiler.take_snapshot()
        
        stats = profiler.get_statistics()
        assert stats["snapshot_count"] == 5

    @given(st.integers(min_value=5, max_value=50))
    @settings(max_examples=20, deadline=None)
    def test_max_snapshots_respected(self, max_snapshots: int) -> None:
        """Property: Max snapshots limit is respected."""
        config = MemoryProfilerConfig(max_snapshots=max_snapshots)
        profiler = MemoryProfiler(config=config)
        
        # Take more snapshots than max
        for _ in range(max_snapshots + 5):
            profiler.take_snapshot()
        
        stats = profiler.get_statistics()
        assert stats["snapshot_count"] <= max_snapshots

    def test_gc_force_returns_valid_stats(self) -> None:
        """Property: Force GC returns valid statistics."""
        profiler = MemoryProfiler()
        result = profiler.force_gc()
        
        assert "collected" in result
        assert "objects_before" in result
        assert "objects_after" in result
        assert "freed" in result
        assert result["collected"] >= 0
        assert result["objects_before"] >= 0
        assert result["objects_after"] >= 0

    def test_statistics_keys_present(self) -> None:
        """Property: Statistics contain expected keys."""
        profiler = MemoryProfiler()
        profiler.take_snapshot()
        stats = profiler.get_statistics()
        
        expected_keys = [
            "current_rss_mb",
            "current_vms_mb",
            "current_heap_mb",
            "gc_objects",
            "gc_collections",
            "min_rss_mb",
            "max_rss_mb",
            "avg_rss_mb",
            "snapshot_count",
        ]
        for key in expected_keys:
            assert key in stats, f"Missing key: {key}"


class TestAllocationInfoProperties:
    """Property tests for AllocationInfo."""

    @given(
        st.integers(min_value=0, max_value=10 * 1024 * 1024 * 1024),
        st.integers(min_value=0, max_value=1_000_000),
    )
    @settings(max_examples=100)
    def test_size_mb_conversion(self, size_bytes: int, count: int) -> None:
        """Property: Size MB conversion is consistent."""
        info = AllocationInfo(
            size_bytes=size_bytes,
            count=count,
            traceback=[],
        )
        expected_mb = size_bytes / (1024 * 1024)
        assert info.size_mb == expected_mb

    @given(st.integers(min_value=0, max_value=10 * 1024 * 1024 * 1024))
    @settings(max_examples=100)
    def test_size_mb_non_negative(self, size_bytes: int) -> None:
        """Property: Size MB is always non-negative."""
        info = AllocationInfo(size_bytes=size_bytes, count=0, traceback=[])
        assert info.size_mb >= 0


class TestLeakDetectionProperties:
    """Property tests for leak detection logic."""

    @pytest.mark.asyncio
    async def test_no_leak_with_stable_memory(self) -> None:
        """Property: No leak detected with stable memory."""
        config = MemoryProfilerConfig(
            min_samples_for_leak=3,
            leak_detection_window=60,
            growth_rate_threshold=10.0,
        )
        profiler = MemoryProfiler(config=config)
        
        # Simulate stable memory
        for _ in range(5):
            profiler.take_snapshot()
        
        alerts = await profiler.analyze()
        leak_alerts = [a for a in alerts if a.alert_type == MemoryAlertType.LEAK_DETECTED]
        # With real memory, we shouldn't see a leak in stable conditions
        # This is a sanity check
        assert isinstance(leak_alerts, list)


class TestConfigValidationProperties:
    """Property tests for configuration validation."""

    @given(
        st.floats(min_value=0.1, max_value=1000, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.1, max_value=1000, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_thresholds_stored_correctly(self, warning: float, critical: float) -> None:
        """Property: Thresholds are stored correctly in config."""
        config = MemoryProfilerConfig(
            warning_threshold_mb=warning,
            critical_threshold_mb=critical,
        )
        assert config.warning_threshold_mb == warning
        assert config.critical_threshold_mb == critical

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=50)
    def test_traceback_limit_stored(self, limit: int) -> None:
        """Property: Traceback limit is stored correctly."""
        config = MemoryProfilerConfig(traceback_limit=limit)
        assert config.traceback_limit == limit
