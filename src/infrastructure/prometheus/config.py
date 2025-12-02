"""Prometheus configuration.

**Feature: observability-infrastructure**
**Requirement: R5 - Prometheus Metrics**
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PrometheusConfig:
    """Configuration for Prometheus metrics.

    Attributes:
        enabled: Whether metrics are enabled
        endpoint: Metrics endpoint path
        include_in_schema: Include endpoint in OpenAPI schema
        namespace: Metrics namespace prefix
        subsystem: Metrics subsystem prefix
        default_buckets: Default histogram buckets
        enable_default_metrics: Enable process/Python metrics
    """

    enabled: bool = True
    endpoint: str = "/metrics"
    include_in_schema: bool = False
    namespace: str = "python_api"
    subsystem: str = ""
    default_buckets: tuple[float, ...] = field(
        default_factory=lambda: (
            0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5,
            0.75, 1.0, 2.5, 5.0, 7.5, 10.0
        )
    )
    enable_default_metrics: bool = True
