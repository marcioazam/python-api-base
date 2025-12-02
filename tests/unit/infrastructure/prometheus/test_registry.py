"""Unit tests for Prometheus registry.

**Feature: observability-infrastructure**
**Requirement: R5 - Prometheus Metrics**
"""

import pytest
from prometheus_client import CollectorRegistry

from infrastructure.prometheus.config import PrometheusConfig
from infrastructure.prometheus.registry import MetricsRegistry


class TestPrometheusConfig:
    """Tests for PrometheusConfig."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = PrometheusConfig()

        assert config.enabled is True
        assert config.endpoint == "/metrics"
        assert config.namespace == "python_api"
        assert len(config.default_buckets) > 0

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = PrometheusConfig(
            namespace="my_app",
            subsystem="api",
            enabled=False,
        )

        assert config.namespace == "my_app"
        assert config.subsystem == "api"
        assert config.enabled is False


class TestMetricsRegistry:
    """Tests for MetricsRegistry."""

    def setup_method(self) -> None:
        """Setup fresh registry for each test."""
        self.test_registry = CollectorRegistry()
        self.config = PrometheusConfig(namespace="test")
        self.registry = MetricsRegistry(self.config, self.test_registry)

    def test_counter_creation(self) -> None:
        """Test counter metric creation."""
        counter = self.registry.counter(
            "requests_total",
            "Total requests",
        )

        counter.inc()
        assert counter._value.get() == 1.0

    def test_counter_with_labels(self) -> None:
        """Test counter with labels."""
        counter = self.registry.counter(
            "requests_labeled",
            "Labeled requests",
            labels=["method", "status"],
        )

        counter.labels(method="GET", status="200").inc()
        counter.labels(method="POST", status="201").inc(2)

    def test_gauge_creation(self) -> None:
        """Test gauge metric creation."""
        gauge = self.registry.gauge(
            "active_connections",
            "Active connections",
        )

        gauge.set(10)
        assert gauge._value.get() == 10.0

        gauge.inc()
        assert gauge._value.get() == 11.0

        gauge.dec(5)
        assert gauge._value.get() == 6.0

    def test_histogram_creation(self) -> None:
        """Test histogram metric creation."""
        histogram = self.registry.histogram(
            "request_duration",
            "Request duration",
        )

        histogram.observe(0.5)
        histogram.observe(1.5)

    def test_histogram_custom_buckets(self) -> None:
        """Test histogram with custom buckets."""
        histogram = self.registry.histogram(
            "custom_duration",
            "Custom duration",
            buckets=(0.1, 0.5, 1.0, 5.0),
        )

        histogram.observe(0.3)

    def test_summary_creation(self) -> None:
        """Test summary metric creation."""
        summary = self.registry.summary(
            "response_size",
            "Response size",
        )

        summary.observe(1024)
        summary.observe(2048)

    def test_metric_caching(self) -> None:
        """Test that metrics are cached."""
        counter1 = self.registry.counter("cached_counter", "Test")
        counter2 = self.registry.counter("cached_counter", "Test")

        assert counter1 is counter2

    def test_full_name_with_namespace(self) -> None:
        """Test full metric name generation."""
        config = PrometheusConfig(namespace="app", subsystem="api")
        registry = MetricsRegistry(config, CollectorRegistry())

        counter = registry.counter("requests", "Total requests")

        # Counter name should include namespace and subsystem
        assert "app_api_requests" in str(counter)

    def test_generate_metrics(self) -> None:
        """Test metrics output generation."""
        self.registry.counter("output_test", "Test counter").inc()

        output = self.registry.generate_metrics()

        assert isinstance(output, bytes)
        assert b"output_test" in output

    def test_content_type(self) -> None:
        """Test content type."""
        content_type = self.registry.content_type()

        assert "text/plain" in content_type or "openmetrics" in content_type
