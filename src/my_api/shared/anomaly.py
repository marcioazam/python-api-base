"""Anomaly Detection for metrics monitoring.

This module provides anomaly detection capabilities using
statistical methods for automatic problem detection.

**Feature: api-architecture-analysis**
**Validates: Requirements 7.3**
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Protocol, runtime_checkable


class AnomalyType(Enum):
    """Types of anomalies."""

    SPIKE = "spike"
    DROP = "drop"
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    OUTLIER = "outlier"
    PATTERN_BREAK = "pattern_break"


class AnomalySeverity(Enum):
    """Severity of detected anomaly."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class DataPoint:
    """A single data point for analysis."""

    value: float
    timestamp: datetime
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class Anomaly:
    """A detected anomaly."""

    anomaly_type: AnomalyType
    severity: AnomalySeverity
    value: float
    expected_value: float
    deviation: float
    timestamp: datetime
    metric_name: str
    description: str = ""

    @property
    def deviation_percent(self) -> float:
        """Get deviation as percentage."""
        if self.expected_value == 0:
            return 100.0 if self.value != 0 else 0.0
        return abs(self.value - self.expected_value) / abs(self.expected_value) * 100


@dataclass
class AnomalyConfig:
    """Configuration for anomaly detection."""

    # Z-score threshold for outlier detection
    z_score_threshold: float = 3.0
    # Minimum data points for analysis
    min_data_points: int = 10
    # Window size for moving average
    window_size: int = 20
    # Spike detection threshold (multiplier of std dev)
    spike_threshold: float = 2.5
    # Trend detection window
    trend_window: int = 10
    # Trend slope threshold
    trend_threshold: float = 0.1
    # Severity thresholds (deviation multipliers)
    warning_threshold: float = 2.0
    critical_threshold: float = 3.0


@runtime_checkable
class AnomalyHandler(Protocol):
    """Protocol for anomaly handling."""

    async def handle(self, anomaly: Anomaly) -> None: ...


class LogAnomalyHandler:
    """Handler that logs anomalies."""

    async def handle(self, anomaly: Anomaly) -> None:
        """Log the anomaly."""
        print(
            f"[ANOMALY] {anomaly.severity.value.upper()}: {anomaly.metric_name} - "
            f"{anomaly.anomaly_type.value} detected. "
            f"Value: {anomaly.value:.2f}, Expected: {anomaly.expected_value:.2f}, "
            f"Deviation: {anomaly.deviation_percent:.1f}%"
        )


class StatisticalAnalyzer:
    """Statistical analysis utilities."""

    @staticmethod
    def mean(values: list[float]) -> float:
        """Calculate mean."""
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def std_dev(values: list[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        avg = StatisticalAnalyzer.mean(values)
        variance = sum((x - avg) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)

    @staticmethod
    def z_score(value: float, mean: float, std_dev: float) -> float:
        """Calculate z-score."""
        if std_dev == 0:
            return 0.0
        return (value - mean) / std_dev

    @staticmethod
    def moving_average(values: list[float], window: int) -> list[float]:
        """Calculate moving average."""
        if len(values) < window:
            return [StatisticalAnalyzer.mean(values)] * len(values)
        result = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            result.append(StatisticalAnalyzer.mean(values[start:i + 1]))
        return result

    @staticmethod
    def linear_regression_slope(values: list[float]) -> float:
        """Calculate slope using linear regression."""
        n = len(values)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2
        y_mean = StatisticalAnalyzer.mean(values)
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        if denominator == 0:
            return 0.0
        return numerator / denominator

    @staticmethod
    def percentile(values: list[float], p: float) -> float:
        """Calculate percentile."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * p)
        return sorted_values[min(index, len(sorted_values) - 1)]


class AnomalyDetector:
    """Detects anomalies in metric data."""

    def __init__(
        self,
        config: AnomalyConfig | None = None,
        handler: AnomalyHandler | None = None,
    ) -> None:
        self._config = config or AnomalyConfig()
        self._handler = handler or LogAnomalyHandler()
        self._data: dict[str, list[DataPoint]] = {}
        self._stats = StatisticalAnalyzer()

    async def record(self, metric_name: str, value: float, labels: dict[str, str] | None = None) -> Anomaly | None:
        """Record a data point and check for anomalies."""
        point = DataPoint(value=value, timestamp=datetime.now(UTC), labels=labels or {})

        if metric_name not in self._data:
            self._data[metric_name] = []
        self._data[metric_name].append(point)

        # Trim old data
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        self._data[metric_name] = [p for p in self._data[metric_name] if p.timestamp > cutoff]

        # Check for anomalies
        anomaly = self._detect_anomaly(metric_name, point)
        if anomaly:
            await self._handler.handle(anomaly)
        return anomaly

    def _detect_anomaly(self, metric_name: str, point: DataPoint) -> Anomaly | None:
        """Detect anomaly in the latest data point."""
        data = self._data.get(metric_name, [])
        if len(data) < self._config.min_data_points:
            return None

        values = [p.value for p in data[:-1]]  # Exclude current point
        current = point.value

        mean = self._stats.mean(values)
        std = self._stats.std_dev(values)

        # Check for outlier using z-score
        z = self._stats.z_score(current, mean, std)
        if abs(z) > self._config.z_score_threshold:
            severity = self._determine_severity(abs(z))
            anomaly_type = AnomalyType.SPIKE if current > mean else AnomalyType.DROP
            return Anomaly(
                anomaly_type=anomaly_type,
                severity=severity,
                value=current,
                expected_value=mean,
                deviation=abs(z),
                timestamp=point.timestamp,
                metric_name=metric_name,
                description=f"Z-score: {z:.2f}",
            )

        # Check for trend
        if len(values) >= self._config.trend_window:
            recent = values[-self._config.trend_window:]
            slope = self._stats.linear_regression_slope(recent)
            normalized_slope = slope / (mean if mean != 0 else 1)

            if abs(normalized_slope) > self._config.trend_threshold:
                anomaly_type = AnomalyType.TREND_UP if slope > 0 else AnomalyType.TREND_DOWN
                return Anomaly(
                    anomaly_type=anomaly_type,
                    severity=AnomalySeverity.WARNING,
                    value=current,
                    expected_value=mean,
                    deviation=abs(normalized_slope),
                    timestamp=point.timestamp,
                    metric_name=metric_name,
                    description=f"Trend slope: {normalized_slope:.4f}",
                )

        return None

    def _determine_severity(self, deviation: float) -> AnomalySeverity:
        """Determine severity based on deviation."""
        if deviation >= self._config.critical_threshold:
            return AnomalySeverity.CRITICAL
        elif deviation >= self._config.warning_threshold:
            return AnomalySeverity.WARNING
        return AnomalySeverity.INFO

    def get_statistics(self, metric_name: str) -> dict[str, float]:
        """Get current statistics for a metric."""
        data = self._data.get(metric_name, [])
        if not data:
            return {"mean": 0, "std_dev": 0, "min": 0, "max": 0, "count": 0}

        values = [p.value for p in data]
        return {
            "mean": self._stats.mean(values),
            "std_dev": self._stats.std_dev(values),
            "min": min(values),
            "max": max(values),
            "count": len(values),
            "p50": self._stats.percentile(values, 0.50),
            "p95": self._stats.percentile(values, 0.95),
            "p99": self._stats.percentile(values, 0.99),
        }


# Convenience factory
def create_anomaly_detector(
    config: AnomalyConfig | None = None,
    handler: AnomalyHandler | None = None,
) -> AnomalyDetector:
    """Create an AnomalyDetector with defaults."""
    return AnomalyDetector(config=config, handler=handler)
