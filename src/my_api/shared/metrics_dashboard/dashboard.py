"""Main dashboard service.

**Feature: code-review-refactoring, Task 18.3: Refactor metrics_dashboard.py**
**Validates: Requirements 5.9**
"""

from datetime import datetime, UTC
from typing import Any

from .enums import ChartType, MetricType, TimeRange
from .models import Dashboard, DashboardData, MetricPoint, MetricSeries, Widget
from .store import InMemoryMetricsStore, MetricsStore


class MetricsDashboard:
    """Main dashboard service."""

    def __init__(self, store: MetricsStore | None = None) -> None:
        self._store = store or InMemoryMetricsStore()
        self._dashboards: dict[str, Dashboard] = {}
        self._default_dashboard = self._create_default_dashboard()
        self._dashboards[self._default_dashboard.id] = self._default_dashboard

    def _create_default_dashboard(self) -> Dashboard:
        """Create default system dashboard."""
        dashboard = Dashboard(id="system", title="System Metrics")

        dashboard.add_widget(
            Widget(
                id="request_rate",
                title="Request Rate",
                chart_type=ChartType.LINE,
                metric_names=["http_requests_total"],
                time_range=TimeRange.LAST_HOUR,
                width=6,
                height=4,
            )
        )

        dashboard.add_widget(
            Widget(
                id="response_time",
                title="Response Time (P95)",
                chart_type=ChartType.LINE,
                metric_names=["http_request_duration_p95"],
                time_range=TimeRange.LAST_HOUR,
                width=6,
                height=4,
            )
        )

        dashboard.add_widget(
            Widget(
                id="error_rate",
                title="Error Rate",
                chart_type=ChartType.AREA,
                metric_names=["http_errors_total"],
                time_range=TimeRange.LAST_HOUR,
                width=6,
                height=4,
            )
        )

        dashboard.add_widget(
            Widget(
                id="active_connections",
                title="Active Connections",
                chart_type=ChartType.GAUGE,
                metric_names=["active_connections"],
                time_range=TimeRange.LAST_5_MINUTES,
                width=6,
                height=4,
            )
        )

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
            points=[
                MetricPoint(
                    timestamp=datetime.now(UTC),
                    value=value,
                    labels=labels or {},
                )
            ],
        )
        await self._store.store_metric(series)

    async def get_dashboard_data(
        self, dashboard_id: str = "system"
    ) -> DashboardData | None:
        """Get dashboard data for rendering."""
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return None

        widget_data = {}
        for widget in dashboard.widgets:
            data = await self._get_widget_data(widget)
            widget_data[widget.id] = data

        return DashboardData(dashboard=dashboard, widget_data=widget_data)

    async def _get_widget_data(self, widget: Widget) -> dict[str, Any]:
        """Get data for a specific widget."""
        metrics = await self._store.get_metrics(widget.metric_names)

        series_data = []
        for name, series in metrics.items():
            if series:
                points = series.get_range(widget.time_range)
                series_data.append(
                    {
                        "name": name,
                        "data": [
                            {
                                "timestamp": p.timestamp.isoformat(),
                                "value": p.value,
                                "labels": p.labels,
                            }
                            for p in points
                        ],
                    }
                )

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
            return False
        return self._dashboards.pop(dashboard_id, None) is not None
