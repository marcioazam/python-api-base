"""Prometheus metrics registry.

**Feature: observability-infrastructure**
**Requirement: R5 - Prometheus Metrics**
"""

from __future__ import annotations

import logging
from typing import Any

from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Summary,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from infrastructure.prometheus.config import PrometheusConfig

logger = logging.getLogger(__name__)

# Global registry instance
_registry: "MetricsRegistry | None" = None


class MetricsRegistry:
    """Central registry for Prometheus metrics.

    Provides a unified interface for creating and managing metrics.

    **Feature: observability-infrastructure**
    **Requirement: R5.1 - Metrics Registry**

    Example:
        >>> registry = MetricsRegistry(config)
        >>> counter = registry.counter("requests_total", "Total requests")
        >>> counter.inc()
    """

    def __init__(
        self,
        config: PrometheusConfig | None = None,
        registry: CollectorRegistry | None = None,
    ) -> None:
        """Initialize metrics registry.

        Args:
            config: Prometheus configuration
            registry: Custom collector registry (defaults to global)
        """
        self._config = config or PrometheusConfig()
        self._registry = registry or REGISTRY
        self._metrics: dict[str, Any] = {}

    @property
    def config(self) -> PrometheusConfig:
        """Get configuration."""
        return self._config

    @property
    def registry(self) -> CollectorRegistry:
        """Get collector registry."""
        return self._registry

    def _full_name(self, name: str) -> str:
        """Build full metric name with namespace/subsystem."""
        parts = []
        if self._config.namespace:
            parts.append(self._config.namespace)
        if self._config.subsystem:
            parts.append(self._config.subsystem)
        parts.append(name)
        return "_".join(parts)

    def counter(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
    ) -> Counter:
        """Create or get a counter metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Label names

        Returns:
            Counter metric
        """
        full_name = self._full_name(name)

        if full_name not in self._metrics:
            self._metrics[full_name] = Counter(
                full_name,
                description,
                labelnames=labels or [],
                registry=self._registry,
            )

        return self._metrics[full_name]

    def gauge(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
    ) -> Gauge:
        """Create or get a gauge metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Label names

        Returns:
            Gauge metric
        """
        full_name = self._full_name(name)

        if full_name not in self._metrics:
            self._metrics[full_name] = Gauge(
                full_name,
                description,
                labelnames=labels or [],
                registry=self._registry,
            )

        return self._metrics[full_name]

    def histogram(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
        buckets: tuple[float, ...] | None = None,
    ) -> Histogram:
        """Create or get a histogram metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Label names
            buckets: Histogram buckets

        Returns:
            Histogram metric
        """
        full_name = self._full_name(name)

        if full_name not in self._metrics:
            self._metrics[full_name] = Histogram(
                full_name,
                description,
                labelnames=labels or [],
                buckets=buckets or self._config.default_buckets,
                registry=self._registry,
            )

        return self._metrics[full_name]

    def summary(
        self,
        name: str,
        description: str,
        labels: list[str] | None = None,
    ) -> Summary:
        """Create or get a summary metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Label names

        Returns:
            Summary metric
        """
        full_name = self._full_name(name)

        if full_name not in self._metrics:
            self._metrics[full_name] = Summary(
                full_name,
                description,
                labelnames=labels or [],
                registry=self._registry,
            )

        return self._metrics[full_name]

    def generate_metrics(self) -> bytes:
        """Generate metrics output.

        Returns:
            Prometheus text format metrics
        """
        return generate_latest(self._registry)

    def content_type(self) -> str:
        """Get metrics content type.

        Returns:
            Prometheus content type header
        """
        return CONTENT_TYPE_LATEST


def get_registry() -> MetricsRegistry:
    """Get the global metrics registry.

    Returns:
        Global MetricsRegistry instance
    """
    global _registry

    if _registry is None:
        _registry = MetricsRegistry()

    return _registry


def set_registry(registry: MetricsRegistry) -> None:
    """Set the global metrics registry.

    Args:
        registry: MetricsRegistry instance
    """
    global _registry
    _registry = registry
