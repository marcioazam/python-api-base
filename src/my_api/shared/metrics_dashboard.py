"""Metrics Dashboard for real-time monitoring visualization.

This module provides a metrics dashboard with real-time updates
and configurable visualizations for system monitoring.

**Feature: api-architecture-analysis**
**Validates: Requirements 7.3**
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Protocol, runtime_checkable


class MetricType(Enum):
    """Types of metrics for dashboard."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    RATE = "rate"
    PERCENTAGE = "percentage"


class ChartType(Enum):
    """Types of charts for visualization."""

    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    GAUGE = "gauge"
    HEATMAP = "heatmap"


class TimeRange(Enum):
    """Time ranges for dashboard views."""

    LAST_5_MINUTES = "5m"
    LAST_15_MINUTES = "15m"
    LAST_HOUR = "1h"
    LAST_6_HOURS = "6h"
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"

    def to_timedelta(self) -> timedelta:
        """Convert to timedelta."""
        mapping = {
            TimeRange.LAST_5_MINUTES: timedelta(minutes=5),
            TimeRange.LAST_15_MINUTES: timedelta(minutes=15),
            TimeRange.LAST_HOUR: timedelta(hours=1),
            TimeRange.LAST_6_HOURS: timedelta(hours=6),
            TimeRange.LAST_24_HOURS: timedelta(days=1),
            TimeRange.LAST_7_DAYS: timedelta(days=7),
            TimeRange.LAST_30_DAYS: timedelta(days=30),
        }
        return mapping.get(self, timedelta(hours=1))


@dataclass(frozen=True)
class MetricPoint:
    """A single metric data point."""

    timestamp: datetime
    value: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """A series of metric points."""

    name: str
    metric_type: MetricType
    points: list[MetricPoint] = field(default_factory=list)
    unit: str = ""
    description: str = ""

    def add_point(self, value: float, labels: dict[str, str] | None = None) -> None:
        """Add a new data point."""
        point = MetricPoint(
            timestamp=datetime.now(),
            value=value,
            labels=labels or {},
        )
        self.points.append(point)

    def get_latest(self) -> MetricPoint | None:
        """Get the latest data point."""
        return self.points[-1] if self.points else None

    def get_range(self, time_range: TimeRange) -> list[MetricPoint]:
        """Get points within time range."""
        cutoff = datetime.now() - time_range.to_timedelta()
        return [p for p in self.points if p.timestamp >= cutoff]

    def calculate_rate(self, time_range: TimeRange) -> float:
        """Calculate rate over time range."""
        points = self.get_range(time_range)
        if len(points) < 2:
            return 0.0

        duration = (points[-1].timestamp - points[0].timestamp).total_seconds()
        if duration == 0:
            return 0.0

        value_diff = points[-1].value - points[0].value
        return value_diff / duration



@dataclass
class Widget:
    """Dashboard widget configuration."""

    id: str
    title: str
    chart_type: ChartType
    metric_names: list[str]
    time_range: TimeRange = TimeRange.LAST_HOUR
    refresh_interval: int = 30  # seconds
    width: int = 6  # grid columns (1-12)
    height: int = 4  # grid rows
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class Dashboard:
    """Dashboard configuration."""

    id: str
    title: str
    widgets: list[Widget] = field(default_factory=list)
    auto_refresh: bool = True
    refresh_interval: int = 30  # seconds
    created_at: datetime = field(default_factory=datetime.now)

    def add_widget(self, widget: Widget) -> None:
        """Add a widget to the dashboard."""
        self.widgets.append(widget)

    def remove_widget(self, widget_id: str) -> bool:
        """Remove a widget by ID."""
        initial_len = len(self.widgets)
        self.widgets = [w for w in self.widgets if w.id != widget_id]
        return len(self.widgets) < initial_len

    def get_widget(self, widget_id: str) -> Widget | None:
        """Get a widget by ID."""
        return next((w for w in self.widgets if w.id == widget_id), None)


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
                existing.points = existing.points[-self._max_points:]
        else:
            self._metrics[series.name] = series

    async def get_metric(self, name: str) -> MetricSeries | None:
        """Get a metric series by name."""
        return self._metrics.get(name)

    async def get_metrics(self, names: list[str]) -> dict[str, MetricSeries]:
        """Get multiple metric series."""
        return {name: series for name, series in self._metrics.items() if name in names}

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
        # Trim old points if exceeding max
        if len(self._metrics[name].points) > self._max_points:
            self._metrics[name].points = self._metrics[name].points[-self._max_points:]


@dataclass
class DashboardData:
    """Data for dashboard rendering."""

    dashboard: Dashboard
    widget_data: dict[str, dict[str, Any]] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_json(self) -> str:
        """Convert to JSON for frontend."""
        data = {
            "dashboard": {
                "id": self.dashboard.id,
                "title": self.dashboard.title,
                "auto_refresh": self.dashboard.auto_refresh,
                "refresh_interval": self.dashboard.refresh_interval,
                "widgets": [
                    {
                        "id": w.id,
                        "title": w.title,
                        "chart_type": w.chart_type.value,
                        "time_range": w.time_range.value,
                        "width": w.width,
                        "height": w.height,
                        "options": w.options,
                    }
                    for w in self.dashboard.widgets
                ],
            },
            "data": self.widget_data,
            "timestamp": self.timestamp.isoformat(),
        }
        return json.dumps(data, default=str)



class MetricsDashboard:
    """Main dashboard service."""

    def __init__(self, store: MetricsStore | None = None) -> None:
        self._store = store or InMemoryMetricsStore()
        self._dashboards: dict[str, Dashboard] = {}
        self._default_dashboard = self._create_default_dashboard()
        self._dashboards[self._default_dashboard.id] = self._default_dashboard

    def _create_default_dashboard(self) -> Dashboard:
        """Create default system dashboard."""
        dashboard = Dashboard(
            id="system",
            title="System Metrics",
        )

        dashboard.add_widget(Widget(
            id="request_rate",
            title="Request Rate",
            chart_type=ChartType.LINE,
            metric_names=["http_requests_total"],
            time_range=TimeRange.LAST_HOUR,
            width=6,
            height=4,
        ))

        dashboard.add_widget(Widget(
            id="response_time",
            title="Response Time (P95)",
            chart_type=ChartType.LINE,
            metric_names=["http_request_duration_p95"],
            time_range=TimeRange.LAST_HOUR,
            width=6,
            height=4,
        ))

        dashboard.add_widget(Widget(
            id="error_rate",
            title="Error Rate",
            chart_type=ChartType.AREA,
            metric_names=["http_errors_total"],
            time_range=TimeRange.LAST_HOUR,
            width=6,
            height=4,
        ))

        dashboard.add_widget(Widget(
            id="active_connections",
            title="Active Connections",
            chart_type=ChartType.GAUGE,
            metric_names=["active_connections"],
            time_range=TimeRange.LAST_5_MINUTES,
            width=6,
            height=4,
        ))

        return dashboard

    async def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a metric value."""
        series = MetricSeries(
            name=name,
            metric_type=metric_type,
            points=[MetricPoint(
                timestamp=datetime.now(),
                value=value,
                labels=labels or {},
            )],
        )
        await self._store.store_metric(series)

    async def get_dashboard_data(self, dashboard_id: str = "system") -> DashboardData | None:
        """Get dashboard data for rendering."""
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return None

        widget_data = {}
        for widget in dashboard.widgets:
            data = await self._get_widget_data(widget)
            widget_data[widget.id] = data

        return DashboardData(
            dashboard=dashboard,
            widget_data=widget_data,
        )

    async def _get_widget_data(self, widget: Widget) -> dict[str, Any]:
        """Get data for a specific widget."""
        metrics = await self._store.get_metrics(widget.metric_names)

        series_data = []
        for name, series in metrics.items():
            if series:
                points = series.get_range(widget.time_range)
                series_data.append({
                    "name": name,
                    "data": [
                        {
                            "timestamp": p.timestamp.isoformat(),
                            "value": p.value,
                            "labels": p.labels,
                        }
                        for p in points
                    ],
                })

        return {
            "series": series_data,
            "chart_type": widget.chart_type.value,
            "time_range": widget.time_range.value,
        }

    def create_dashboard(self, dashboard: Dashboard) -> None:
        """Create a new dashboard."""
        self._dashboards[dashboard.id] = dashboard

    def get_dashboard(self, dashboard_id: str) -> Dashboard | None:
        """Get a dashboard by ID."""
        return self._dashboards.get(dashboard_id)

    def list_dashboards(self) -> list[Dashboard]:
        """List all dashboards."""
        return list(self._dashboards.values())

    def delete_dashboard(self, dashboard_id: str) -> bool:
        """Delete a dashboard."""
        if dashboard_id == "system":
            return False  # Cannot delete system dashboard
        return self._dashboards.pop(dashboard_id, None) is not None


class DashboardBuilder:
    """Fluent builder for dashboards."""

    def __init__(self, dashboard_id: str, title: str) -> None:
        self._dashboard = Dashboard(id=dashboard_id, title=title)

    def add_line_chart(
        self,
        widget_id: str,
        title: str,
        metrics: list[str],
        time_range: TimeRange = TimeRange.LAST_HOUR,
        width: int = 6,
    ) -> "DashboardBuilder":
        """Add a line chart widget."""
        widget = Widget(
            id=widget_id,
            title=title,
            chart_type=ChartType.LINE,
            metric_names=metrics,
            time_range=time_range,
            width=width,
        )
        self._dashboard.add_widget(widget)
        return self

    def add_gauge(
        self,
        widget_id: str,
        title: str,
        metric: str,
        min_value: float = 0,
        max_value: float = 100,
        width: int = 3,
    ) -> "DashboardBuilder":
        """Add a gauge widget."""
        widget = Widget(
            id=widget_id,
            title=title,
            chart_type=ChartType.GAUGE,
            metric_names=[metric],
            time_range=TimeRange.LAST_5_MINUTES,
            width=width,
            options={"min": min_value, "max": max_value},
        )
        self._dashboard.add_widget(widget)
        return self

    def add_bar_chart(
        self,
        widget_id: str,
        title: str,
        metrics: list[str],
        time_range: TimeRange = TimeRange.LAST_HOUR,
        width: int = 6,
    ) -> "DashboardBuilder":
        """Add a bar chart widget."""
        widget = Widget(
            id=widget_id,
            title=title,
            chart_type=ChartType.BAR,
            metric_names=metrics,
            time_range=time_range,
            width=width,
        )
        self._dashboard.add_widget(widget)
        return self

    def build(self) -> Dashboard:
        """Build the dashboard."""
        return self._dashboard


# Convenience factory
def create_metrics_dashboard(store: MetricsStore | None = None) -> MetricsDashboard:
    """Create a MetricsDashboard with defaults."""
    return MetricsDashboard(store=store)


def create_performance_dashboard() -> Dashboard:
    """Create a pre-configured performance dashboard."""
    return (
        DashboardBuilder("performance", "Performance Metrics")
        .add_line_chart(
            "cpu_usage",
            "CPU Usage",
            ["cpu_usage_percent"],
            TimeRange.LAST_HOUR,
        )
        .add_line_chart(
            "memory_usage",
            "Memory Usage",
            ["memory_usage_percent"],
            TimeRange.LAST_HOUR,
        )
        .add_gauge(
            "disk_usage",
            "Disk Usage",
            "disk_usage_percent",
            0,
            100,
        )
        .add_bar_chart(
            "top_endpoints",
            "Top Endpoints by Requests",
            ["endpoint_requests"],
            TimeRange.LAST_24_HOURS,
        )
        .build()
    )
