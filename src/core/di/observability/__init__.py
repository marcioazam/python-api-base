"""Container observability and metrics.

Contains metrics tracking, hooks, and statistics for container usage.

**Feature: core-di-restructuring-2025**
"""

from core.di.observability.metrics import (
    ContainerHooks,
    ContainerStats,
    MetricsTracker,
)

__all__ = [
    "ContainerHooks",
    "ContainerStats",
    "MetricsTracker",
]
