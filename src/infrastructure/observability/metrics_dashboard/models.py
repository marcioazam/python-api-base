"""Metrics dashboard models.

**Feature: code-review-refactoring, Task 18.3: Refactor metrics_dashboard.py**
**Validates: Requirements 5.9**
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from .enums import ChartType, MetricType, TimeRange


@dataclass(frozen=True, slots=True)
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
            timestamp=datetime.now(UTC),
            value=value,
            labels=labels or {},
        )
        self.points.append(point)

    def get_latest(self) -> MetricPoint | None:
        """Get the latest data point."""
        return self.points[-1] if self.points else None

    def get_range(self, time_range: TimeRange) -> list[MetricPoint]:
        """Get points within time range."""
        cutoff = datetime.now(UTC) - time_range.to_timedelta()
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
    refresh_interval: int = 30
    width: int = 6
    height: int = 4
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class Dashboard:
    """Dashboard configuration."""

    id: str
    title: str
    widgets: list[Widget] = field(default_factory=list)
    auto_refresh: bool = True
    refresh_interval: int = 30
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

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


@dataclass
class DashboardData:
    """Data for dashboard rendering."""

    dashboard: Dashboard
    widget_data: dict[str, dict[str, Any]] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

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
