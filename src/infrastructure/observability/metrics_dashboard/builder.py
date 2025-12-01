"""Dashboard builder.

**Feature: code-review-refactoring, Task 18.3: Refactor metrics_dashboard.py**
**Validates: Requirements 5.9**
"""

from .dashboard import MetricsDashboard
from .enums import ChartType, TimeRange
from .models import Dashboard, Widget
from .store import MetricsStore


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
