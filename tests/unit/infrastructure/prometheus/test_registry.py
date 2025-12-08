"""Tests for Prometheus metrics registry module.

Tests for MetricsRegistry, get_registry, and set_registry.
"""

import pytest
from prometheus_client import CollectorRegistry

from infrastructure.prometheus.config import PrometheusConfig
from infrastructure.prometheus.registry import (
    MetricsRegistry,
    get_registry,
    set_registry,
)


class TestMetricsRegistry:
    """Tests for MetricsRegistry class."""

    def test_init_default_config(self) -> None:
        """Registry should use default config when none provided."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)
        assert metrics.config is not None

    def test_init_custom_config(self) -> None:
        """Registry should use provided config."""
        config = PrometheusConfig(namespace="test")
        registry = CollectorRegistry()
        metrics = MetricsRegistry(config=config, registry=registry)
        assert metrics.config.namespace == "test"

    def test_config_property(self) -> None:
        """config property should return config."""
        config = PrometheusConfig()
        registry = CollectorRegistry()
        metrics = MetricsRegistry(config=config, registry=registry)
        assert metrics.config == config

    def test_registry_property(self) -> None:
        """registry property should return collector registry."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)
        assert metrics.registry == registry

    def test_full_name_with_namespace(self) -> None:
        """_full_name should include namespace."""
        config = PrometheusConfig(namespace="myapp")
        registry = CollectorRegistry()
        metrics = MetricsRegistry(config=config, registry=registry)
        assert metrics._full_name("requests") == "myapp_requests"

    def test_full_name_with_subsystem(self) -> None:
        """_full_name should include subsystem."""
        config = PrometheusConfig(namespace="", subsystem="http")
        registry = CollectorRegistry()
        metrics = MetricsRegistry(config=config, registry=registry)
        assert metrics._full_name("requests") == "http_requests"

    def test_full_name_with_namespace_and_subsystem(self) -> None:
        """_full_name should include both namespace and subsystem."""
        config = PrometheusConfig(namespace="myapp", subsystem="http")
        registry = CollectorRegistry()
        metrics = MetricsRegistry(config=config, registry=registry)
        assert metrics._full_name("requests") == "myapp_http_requests"

    def test_full_name_without_prefix(self) -> None:
        """_full_name should work without namespace/subsystem."""
        config = PrometheusConfig(namespace="", subsystem="")
        registry = CollectorRegistry()
        metrics = MetricsRegistry(config=config, registry=registry)
        assert metrics._full_name("requests") == "requests"

    def test_counter_creates_metric(self) -> None:
        """counter should create a Counter metric."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)
        counter = metrics.counter("test_counter", "Test counter")
        assert counter is not None
        counter.inc()

    def test_counter_returns_same_metric(self) -> None:
        """counter should return same metric for same name."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)
        counter1 = metrics.counter("same_counter", "Test")
        counter2 = metrics.counter("same_counter", "Test")
        assert counter1 is counter2

    def test_counter_with_labels(self) -> None:
        """counter should support labels."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)
        counter = metrics.counter("labeled_counter", "Test", labels=["method"])
        counter.labels(method="GET").inc()

    def test_gauge_creates_metric(self) -> None:
        """gauge should create a Gauge metric."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)
        gauge = metrics.gauge("test_gauge", "Test gauge")
        assert gauge is not None
        gauge.set(42)

    def test_gauge_returns_same_metric(self) -> None:
        """gauge should return same metric for same name."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)
        gauge1 = metrics.gauge("same_gauge", "Test")
        gauge2 = metrics.gauge("same_gauge", "Test")
        assert gauge1 is gauge2

    def test_gauge_with_labels(self) -> None:
        """gauge should support labels."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)
        gauge = metrics.gauge("labeled_gauge", "Test", labels=["status"])
        gauge.labels(status="active").set(10)

    def test_histogram_creates_metric(self) -> None:
        """histogram should create a Histogram metric."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)
        histogram = metrics.histogram("test_histogram", "Test histogram")
        assert histogram is not None
        histogram.observe(0.5)

    def test_histogram_returns_same_metric(self) -> None:
        """histogram should return same metric for same name."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)
        hist1 = metrics.histogram("same_histogram", "Test")
        hist2 = metrics.histogram("same_histogram", "Test")
        assert hist1 is hist2

    def test_histogram_with_custom_buckets(self) -> None:
        """histogram should support custom buckets."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)
        buckets = (0.1, 0.5, 1.0, 5.0)
        histogram = metrics.histogram(
            "custom_buckets_histogram", "Test", buckets=buckets
        )
        histogram.observe(0.3)

    def test_summary_creates_metric(self) -> None:
        """summary should create a Summary metric."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)
        summary = metrics.summary("test_summary", "Test summary")
        assert summary is not None
        summary.observe(0.5)

    def test_summary_returns_same_metric(self) -> None:
        """summary should return same metric for same name."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)
        sum1 = metrics.summary("same_summary", "Test")
        sum2 = metrics.summary("same_summary", "Test")
        assert sum1 is sum2

    def test_generate_metrics_returns_bytes(self) -> None:
        """generate_metrics should return bytes."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)
        metrics.counter("gen_test", "Test").inc()
        output = metrics.generate_metrics()
        assert isinstance(output, bytes)

    def test_content_type_returns_string(self) -> None:
        """content_type should return content type string."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)
        content_type = metrics.content_type()
        assert isinstance(content_type, str)
        assert "text/plain" in content_type or "openmetrics" in content_type


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def test_get_registry_returns_instance(self) -> None:
        """get_registry should return MetricsRegistry instance."""
        registry = get_registry()
        assert isinstance(registry, MetricsRegistry)

    def test_set_registry_changes_global(self) -> None:
        """set_registry should change global registry."""
        custom_registry = CollectorRegistry()
        custom_metrics = MetricsRegistry(registry=custom_registry)
        set_registry(custom_metrics)
        assert get_registry() is custom_metrics
