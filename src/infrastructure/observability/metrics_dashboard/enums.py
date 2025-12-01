"""Metrics dashboard enums.

**Feature: code-review-refactoring, Task 18.3: Refactor metrics_dashboard.py**
**Validates: Requirements 5.9**
"""

from datetime import timedelta
from enum import Enum


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
