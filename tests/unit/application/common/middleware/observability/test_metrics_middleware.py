"""Tests for metrics middleware module.

Tests for MetricsCollector, InMemoryMetricsCollector, MetricsConfig, MetricsMiddleware.
"""

import pytest

from application.common.middleware.observability.metrics_middleware import (
    InMemoryMetricsCollector,
    MetricsCollector,
    MetricsConfig,
    MetricsMiddleware,
)


class TestMetricsCollectorProtocol:
    """Tests for MetricsCollector protocol."""

    def test_in_memory_collector_is_metrics_collector(self) -> None:
        """InMemoryMetricsCollector should implement MetricsCollector."""
        collector = InMemoryMetricsCollector()
        assert isinstance(collector, MetricsCollector)


class TestInMemoryMetricsCollector:
    """Tests for InMemoryMetricsCollector class."""

    def test_init_empty_durations(self) -> None:
        """Collector should start with empty durations."""
        collector = InMemoryMetricsCollector()
        assert len(collector._durations) == 0

    def test_init_empty_counts(self) -> None:
        """Collector should start with empty counts."""
        collector = InMemoryMetricsCollector()
        assert len(collector._counts) == 0

    def test_init_empty_slow_commands(self) -> None:
        """Collector should start with empty slow commands."""
        collector = InMemoryMetricsCollector()
        assert len(collector._slow_commands) == 0

    def test_record_command_duration(self) -> None:
        """record_command_duration should store duration."""
        collector = InMemoryMetricsCollector()
        collector.record_command_duration("TestCommand", 100.5, True)
        assert "TestCommand" in collector._durations
        assert 100.5 in collector._durations["TestCommand"]

    def test_record_multiple_durations(self) -> None:
        """Should record multiple durations for same command."""
        collector = InMemoryMetricsCollector()
        collector.record_command_duration("TestCommand", 100.0, True)
        collector.record_command_duration("TestCommand", 200.0, True)
        collector.record_command_duration("TestCommand", 150.0, False)
        assert len(collector._durations["TestCommand"]) == 3

    def test_increment_command_count_success(self) -> None:
        """increment_command_count should track success."""
        collector = InMemoryMetricsCollector()
        collector.increment_command_count("TestCommand", True)
        assert collector._counts["TestCommand"]["success"] == 1
        assert collector._counts["TestCommand"]["failure"] == 0

    def test_increment_command_count_failure(self) -> None:
        """increment_command_count should track failure."""
        collector = InMemoryMetricsCollector()
        collector.increment_command_count("TestCommand", False)
        assert collector._counts["TestCommand"]["success"] == 0
        assert collector._counts["TestCommand"]["failure"] == 1

    def test_increment_multiple_counts(self) -> None:
        """Should track multiple increments."""
        collector = InMemoryMetricsCollector()
        collector.increment_command_count("TestCommand", True)
        collector.increment_command_count("TestCommand", True)
        collector.increment_command_count("TestCommand", False)
        assert collector._counts["TestCommand"]["success"] == 2
        assert collector._counts["TestCommand"]["failure"] == 1

    def test_record_slow_command(self) -> None:
        """record_slow_command should store slow command info."""
        collector = InMemoryMetricsCollector()
        collector.record_slow_command("SlowCommand", 5000.0)
        assert len(collector._slow_commands) == 1
        assert collector._slow_commands[0][0] == "SlowCommand"
        assert collector._slow_commands[0][1] == 5000.0

    def test_get_statistics_single_command(self) -> None:
        """get_statistics should return stats for single command."""
        collector = InMemoryMetricsCollector()
        collector.record_command_duration("TestCommand", 100.0, True)
        collector.record_command_duration("TestCommand", 200.0, True)
        collector.increment_command_count("TestCommand", True)
        collector.increment_command_count("TestCommand", True)
        stats = collector.get_statistics("TestCommand")
        assert stats["command_type"] == "TestCommand"
        assert stats["total_executions"] == 2
        assert stats["success_count"] == 2
        assert stats["failure_count"] == 0
        assert stats["success_rate"] == 1.0
        assert stats["avg_duration_ms"] == 150.0
        assert stats["min_duration_ms"] == 100.0
        assert stats["max_duration_ms"] == 200.0

    def test_get_statistics_all_commands(self) -> None:
        """get_statistics without arg should return all stats."""
        collector = InMemoryMetricsCollector()
        collector.increment_command_count("Command1", True)
        collector.increment_command_count("Command2", False)
        stats = collector.get_statistics()
        assert "commands" in stats
        assert "total_commands" in stats
        assert stats["total_commands"] == 2

    def test_get_statistics_empty(self) -> None:
        """get_statistics should handle empty data."""
        collector = InMemoryMetricsCollector()
        stats = collector.get_statistics("NonExistent")
        assert stats["total_executions"] == 0
        assert stats["success_rate"] == 0
        assert stats["avg_duration_ms"] == 0

    def test_success_rate_calculation(self) -> None:
        """Success rate should be calculated correctly."""
        collector = InMemoryMetricsCollector()
        collector.increment_command_count("TestCommand", True)
        collector.increment_command_count("TestCommand", True)
        collector.increment_command_count("TestCommand", False)
        collector.increment_command_count("TestCommand", False)
        stats = collector.get_statistics("TestCommand")
        assert stats["success_rate"] == 0.5


class TestMetricsConfig:
    """Tests for MetricsConfig dataclass."""

    def test_default_values(self) -> None:
        """Config should have sensible defaults."""
        config = MetricsConfig()
        assert config.enabled is True
        assert config.track_duration is True
        assert config.track_success_rate is True
        assert config.detect_slow_commands is True
        assert config.slow_threshold_ms == 1000.0

    def test_custom_values(self) -> None:
        """Config should accept custom values."""
        config = MetricsConfig(
            enabled=False,
            track_duration=False,
            track_success_rate=False,
            detect_slow_commands=False,
            slow_threshold_ms=500.0,
        )
        assert config.enabled is False
        assert config.track_duration is False
        assert config.track_success_rate is False
        assert config.detect_slow_commands is False
        assert config.slow_threshold_ms == 500.0

    def test_is_frozen(self) -> None:
        """Config should be immutable."""
        config = MetricsConfig()
        with pytest.raises(AttributeError):
            config.enabled = False  # type: ignore


class TestMetricsMiddleware:
    """Tests for MetricsMiddleware class."""

    def test_init_with_collector(self) -> None:
        """Middleware should store collector."""
        collector = InMemoryMetricsCollector()
        middleware = MetricsMiddleware(collector)
        assert middleware._collector is collector

    def test_init_default_config(self) -> None:
        """Middleware should use default config if not provided."""
        collector = InMemoryMetricsCollector()
        middleware = MetricsMiddleware(collector)
        assert middleware._config.enabled is True

    def test_init_custom_config(self) -> None:
        """Middleware should use provided config."""
        collector = InMemoryMetricsCollector()
        config = MetricsConfig(enabled=False)
        middleware = MetricsMiddleware(collector, config)
        assert middleware._config.enabled is False

    @pytest.mark.asyncio
    async def test_call_disabled(self) -> None:
        """Middleware should pass through when disabled."""
        collector = InMemoryMetricsCollector()
        config = MetricsConfig(enabled=False)
        middleware = MetricsMiddleware(collector, config)

        async def handler(cmd: str) -> str:
            return f"handled: {cmd}"

        result = await middleware("test", handler)
        assert result == "handled: test"
        assert len(collector._durations) == 0

    @pytest.mark.asyncio
    async def test_call_records_duration(self) -> None:
        """Middleware should record duration."""
        collector = InMemoryMetricsCollector()
        middleware = MetricsMiddleware(collector)

        async def handler(cmd: str) -> str:
            return f"handled: {cmd}"

        await middleware("test", handler)
        assert "str" in collector._durations

    @pytest.mark.asyncio
    async def test_call_records_success(self) -> None:
        """Middleware should record success count."""
        collector = InMemoryMetricsCollector()
        middleware = MetricsMiddleware(collector)

        async def handler(cmd: str) -> str:
            return "ok"

        await middleware("test", handler)
        assert collector._counts["str"]["success"] == 1

    @pytest.mark.asyncio
    async def test_call_records_failure(self) -> None:
        """Middleware should record failure count on exception."""
        collector = InMemoryMetricsCollector()
        middleware = MetricsMiddleware(collector)

        async def handler(cmd: str) -> str:
            raise ValueError("error")

        with pytest.raises(ValueError):
            await middleware("test", handler)
        assert collector._counts["str"]["failure"] == 1

    @pytest.mark.asyncio
    async def test_call_detects_slow_command(self) -> None:
        """Middleware should detect slow commands."""
        import asyncio

        collector = InMemoryMetricsCollector()
        config = MetricsConfig(slow_threshold_ms=1.0)  # Very low threshold
        middleware = MetricsMiddleware(collector, config)

        async def slow_handler(cmd: str) -> str:
            await asyncio.sleep(0.01)  # 10ms
            return "ok"

        await middleware("test", slow_handler)
        assert len(collector._slow_commands) == 1

    @pytest.mark.asyncio
    async def test_call_returns_result(self) -> None:
        """Middleware should return handler result."""
        collector = InMemoryMetricsCollector()
        middleware = MetricsMiddleware(collector)

        async def handler(cmd: str) -> dict:
            return {"status": "ok", "data": cmd}

        result = await middleware("test", handler)
        assert result == {"status": "ok", "data": "test"}

    @pytest.mark.asyncio
    async def test_call_no_duration_tracking(self) -> None:
        """Middleware should skip duration tracking if disabled."""
        collector = InMemoryMetricsCollector()
        config = MetricsConfig(track_duration=False)
        middleware = MetricsMiddleware(collector, config)

        async def handler(cmd: str) -> str:
            return "ok"

        await middleware("test", handler)
        assert len(collector._durations) == 0

    @pytest.mark.asyncio
    async def test_call_no_success_rate_tracking(self) -> None:
        """Middleware should skip success rate tracking if disabled."""
        collector = InMemoryMetricsCollector()
        config = MetricsConfig(track_success_rate=False)
        middleware = MetricsMiddleware(collector, config)

        async def handler(cmd: str) -> str:
            return "ok"

        await middleware("test", handler)
        assert len(collector._counts) == 0

    @pytest.mark.asyncio
    async def test_call_no_slow_detection(self) -> None:
        """Middleware should skip slow detection if disabled."""
        import asyncio

        collector = InMemoryMetricsCollector()
        config = MetricsConfig(detect_slow_commands=False, slow_threshold_ms=1.0)
        middleware = MetricsMiddleware(collector, config)

        async def slow_handler(cmd: str) -> str:
            await asyncio.sleep(0.01)
            return "ok"

        await middleware("test", slow_handler)
        assert len(collector._slow_commands) == 0
