"""Prometheus metrics infrastructure.

Provides metrics collection, decorators, and FastAPI integration.

**Feature: observability-infrastructure**
**Requirement: R5 - Prometheus Metrics**
"""

from infrastructure.prometheus.config import PrometheusConfig
from infrastructure.prometheus.registry import (
    MetricsRegistry,
    get_registry,
)
from infrastructure.prometheus.metrics import (
    counter,
    gauge,
    histogram,
    summary,
    timer,
    count_exceptions,
)
from infrastructure.prometheus.middleware import PrometheusMiddleware
from infrastructure.prometheus.endpoint import create_metrics_endpoint, setup_prometheus

__all__ = [
    # Config
    "PrometheusConfig",
    # Registry
    "MetricsRegistry",
    "get_registry",
    # Metrics decorators
    "counter",
    "gauge",
    "histogram",
    "summary",
    "timer",
    "count_exceptions",
    # FastAPI
    "PrometheusMiddleware",
    "create_metrics_endpoint",
    "setup_prometheus",
]
