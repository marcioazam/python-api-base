"""Metrics storage.

**Feature: code-review-refactoring, Task 18.3: Refactor metrics_dashboard.py**
**Validates: Requirements 5.9**
"""

from typing import Protocol, runtime_checkable

from .enums import MetricType
from .models import MetricSeries


@runtime_checkable
class MetricsStore(Protocol):
    """Protocol for metrics storage."""

    async def store_metric(self, series: MetricSeries) -> None: ...
    async def get_metric(self, name: str) -> MetricSeries | None: ...
    async def get_metrics(self, names: list[str]) -> dict[str, MetricSeries]: ...
    async def list_metrics(self) -> list[str]: ...


class InMemoryMetricsStore:
    """In-memory implementation of MetricsStore."""

    def __init__(self, max_points_per_series: int = 10000) -> None:
        self._metrics: dict[str, MetricSeries] = {}
        self._max_points = max_points_per_series

    async def store_metric(self, series: MetricSeries) -> None:
        """Store a metric series."""
        if series.name in self._metrics:
            existing = self._metrics[series.name]
            existing.points.extend(series.points)
            if len(existing.points) > self._max_points:
                existing.points = existing.points[-self._max_points :]
        else:
            self._metrics[series.name] = series

    async def get_metric(self, name: str) -> MetricSeries | None:
        """Get a metric series by name."""
        return self._metrics.get(name)

    async def get_metrics(self, names: list[str]) -> dict[str, MetricSeries]:
        """Get multiple metric series."""
        return {
            name: series for name, series in self._metrics.items() if name in names
        }

    async def list_metrics(self) -> list[str]:
        """List all metric names."""
        return list(self._metrics.keys())

    def record_value(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Record a single metric value."""
        if name not in self._metrics:
            self._metrics[name] = MetricSeries(
                name=name,
                metric_type=MetricType.GAUGE,
            )
        self._metrics[name].add_point(value, labels)
        if len(self._metrics[name].points) > self._max_points:
            self._metrics[name].points = self._metrics[name].points[-self._max_points :]
