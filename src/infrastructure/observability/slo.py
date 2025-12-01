"""SLO (Service Level Objective) Monitoring.

This module provides SLO monitoring capabilities with configurable
targets and alerting when SLOs are violated.

**Feature: api-architecture-analysis**
**Validates: Requirements 7.3**
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class SLOType(Enum):
    """Types of SLO metrics."""

    AVAILABILITY = "availability"
    LATENCY_P50 = "latency_p50"
    LATENCY_P90 = "latency_p90"
    LATENCY_P95 = "latency_p95"
    LATENCY_P99 = "latency_p99"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    SATURATION = "saturation"


class SLOStatus(Enum):
    """Status of an SLO."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SLOTarget:
    """Definition of an SLO target."""

    name: str
    slo_type: SLOType
    target_value: float
    warning_threshold: float | None = None
    window: timedelta = field(default_factory=lambda: timedelta(hours=1))
    description: str = ""

    def __post_init__(self) -> None:
        if self.warning_threshold is None:
            # Default warning at 95% of target
            object.__setattr__(self, "warning_threshold", self.target_value * 0.95)


@dataclass
class SLOMetric:
    """A recorded SLO metric value."""

    slo_type: SLOType
    value: float
    timestamp: datetime
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class SLOResult:
    """Result of an SLO check."""

    target: SLOTarget
    current_value: float
    status: SLOStatus
    error_budget_remaining: float
    samples: int
    window_start: datetime
    window_end: datetime
    details: str = ""

    @property
    def is_healthy(self) -> bool:
        """Check if SLO is healthy."""
        return self.status == SLOStatus.HEALTHY

    @property
    def is_violated(self) -> bool:
        """Check if SLO is violated."""
        return self.status == SLOStatus.CRITICAL


@runtime_checkable
class MetricsStore(Protocol):
    """Protocol for metrics storage."""

    async def record(self, metric: SLOMetric) -> None: ...
    async def get_metrics(
        self, slo_type: SLOType, since: datetime, labels: dict[str, str] | None = None
    ) -> list[SLOMetric]: ...


@runtime_checkable
class AlertHandler(Protocol):
    """Protocol for alert handling."""

    async def send_alert(self, result: SLOResult) -> None: ...


class InMemoryMetricsStore:
    """In-memory implementation of MetricsStore."""

    def __init__(self, max_size: int = 10000) -> None:
        self._metrics: list[SLOMetric] = []
        self._max_size = max_size

    async def record(self, metric: SLOMetric) -> None:
        """Record a metric."""
        self._metrics.append(metric)
        # Trim old metrics if needed
        if len(self._metrics) > self._max_size:
            self._metrics = self._metrics[-self._max_size:]

    async def get_metrics(
        self, slo_type: SLOType, since: datetime, labels: dict[str, str] | None = None
    ) -> list[SLOMetric]:
        """Get metrics since timestamp."""
        result = [
            m for m in self._metrics
            if m.slo_type == slo_type and m.timestamp >= since
        ]
        if labels:
            result = [
                m for m in result
                if all(m.labels.get(k) == v for k, v in labels.items())
            ]
        return result


class LogAlertHandler:
    """Alert handler that logs alerts."""

    def __init__(self, logger: Any = None) -> None:
        self._logger = logger

    async def send_alert(self, result: SLOResult) -> None:
        """Log an alert."""
        message = (
            f"SLO Alert: {result.target.name} is {result.status.value}. "
            f"Current: {result.current_value:.4f}, Target: {result.target.target_value:.4f}, "
            f"Error budget remaining: {result.error_budget_remaining:.2%}"
        )
        if self._logger:
            self._logger.warning(message)
        else:
            print(f"[ALERT] {message}")


@dataclass
class SLOConfig:
    """Configuration for SLO monitoring."""

    targets: list[SLOTarget] = field(default_factory=list)
    check_interval: timedelta = field(default_factory=lambda: timedelta(minutes=1))
    alert_on_warning: bool = False
    alert_on_critical: bool = True
    error_budget_period: timedelta = field(default_factory=lambda: timedelta(days=30))

    @classmethod
    def default(cls) -> "SLOConfig":
        """Create default configuration with common SLOs."""
        return cls(
            targets=[
                SLOTarget(
                    name="availability",
                    slo_type=SLOType.AVAILABILITY,
                    target_value=0.999,  # 99.9%
                    warning_threshold=0.995,
                    description="Service availability",
                ),
                SLOTarget(
                    name="latency_p99",
                    slo_type=SLOType.LATENCY_P99,
                    target_value=200.0,  # 200ms
                    warning_threshold=150.0,
                    description="99th percentile latency in ms",
                ),
                SLOTarget(
                    name="error_rate",
                    slo_type=SLOType.ERROR_RATE,
                    target_value=0.01,  # 1%
                    warning_threshold=0.005,
                    description="Error rate",
                ),
            ]
        )


class SLOMonitor:
    """Service for monitoring SLOs."""

    def __init__(
        self,
        config: SLOConfig,
        store: MetricsStore,
        alert_handler: AlertHandler | None = None,
    ) -> None:
        self._config = config
        self._store = store
        self._alert_handler = alert_handler or LogAlertHandler()
        self._target_map = {t.name: t for t in config.targets}

    async def record_availability(
        self, is_available: bool, labels: dict[str, str] | None = None
    ) -> None:
        """Record an availability data point."""
        metric = SLOMetric(
            slo_type=SLOType.AVAILABILITY,
            value=1.0 if is_available else 0.0,
            timestamp=datetime.now(UTC),
            labels=labels or {},
        )
        await self._store.record(metric)

    async def record_latency(
        self, latency_ms: float, labels: dict[str, str] | None = None
    ) -> None:
        """Record a latency data point."""
        # Record for all latency percentile types
        for slo_type in [
            SLOType.LATENCY_P50,
            SLOType.LATENCY_P90,
            SLOType.LATENCY_P95,
            SLOType.LATENCY_P99,
        ]:
            metric = SLOMetric(
                slo_type=slo_type,
                value=latency_ms,
                timestamp=datetime.now(UTC),
                labels=labels or {},
            )
            await self._store.record(metric)

    async def record_error(
        self, is_error: bool, labels: dict[str, str] | None = None
    ) -> None:
        """Record an error data point."""
        metric = SLOMetric(
            slo_type=SLOType.ERROR_RATE,
            value=1.0 if is_error else 0.0,
            timestamp=datetime.now(UTC),
            labels=labels or {},
        )
        await self._store.record(metric)

    async def check_slo(self, target_name: str) -> SLOResult:
        """Check a specific SLO."""
        target = self._target_map.get(target_name)
        if not target:
            return SLOResult(
                target=SLOTarget(name=target_name, slo_type=SLOType.AVAILABILITY, target_value=0),
                current_value=0,
                status=SLOStatus.UNKNOWN,
                error_budget_remaining=0,
                samples=0,
                window_start=datetime.now(UTC),
                window_end=datetime.now(UTC),
                details=f"Unknown SLO target: {target_name}",
            )

        window_end = datetime.now(UTC)
        window_start = window_end - target.window

        metrics = await self._store.get_metrics(target.slo_type, window_start)

        if not metrics:
            return SLOResult(
                target=target,
                current_value=0,
                status=SLOStatus.UNKNOWN,
                error_budget_remaining=1.0,
                samples=0,
                window_start=window_start,
                window_end=window_end,
                details="No metrics available",
            )

        current_value = self._calculate_value(target.slo_type, metrics)
        status = self._determine_status(target, current_value)
        error_budget = self._calculate_error_budget(target, current_value)

        result = SLOResult(
            target=target,
            current_value=current_value,
            status=status,
            error_budget_remaining=error_budget,
            samples=len(metrics),
            window_start=window_start,
            window_end=window_end,
        )

        # Send alert if needed
        if status == SLOStatus.CRITICAL and self._config.alert_on_critical:
            await self._alert_handler.send_alert(result)
        elif status == SLOStatus.WARNING and self._config.alert_on_warning:
            await self._alert_handler.send_alert(result)

        return result

    async def check_all_slos(self) -> list[SLOResult]:
        """Check all configured SLOs."""
        results = []
        for target in self._config.targets:
            result = await self.check_slo(target.name)
            results.append(result)
        return results

    def _calculate_value(self, slo_type: SLOType, metrics: list[SLOMetric]) -> float:
        """Calculate the current SLO value from metrics."""
        if not metrics:
            return 0.0

        values = [m.value for m in metrics]

        if slo_type == SLOType.AVAILABILITY:
            return sum(values) / len(values)
        elif slo_type == SLOType.ERROR_RATE:
            return sum(values) / len(values)
        elif slo_type in (SLOType.LATENCY_P50, SLOType.LATENCY_P90, SLOType.LATENCY_P95, SLOType.LATENCY_P99):
            sorted_values = sorted(values)
            percentile_map = {
                SLOType.LATENCY_P50: 0.50,
                SLOType.LATENCY_P90: 0.90,
                SLOType.LATENCY_P95: 0.95,
                SLOType.LATENCY_P99: 0.99,
            }
            percentile = percentile_map.get(slo_type, 0.99)
            index = int(len(sorted_values) * percentile)
            return sorted_values[min(index, len(sorted_values) - 1)]
        elif slo_type == SLOType.THROUGHPUT:
            return sum(values)
        else:
            return sum(values) / len(values)

    def _determine_status(self, target: SLOTarget, current_value: float) -> SLOStatus:
        """Determine SLO status based on current value."""
        # For latency and error rate, lower is better
        if target.slo_type in (SLOType.ERROR_RATE,):
            if current_value <= target.target_value:
                return SLOStatus.HEALTHY
            elif target.warning_threshold and current_value <= target.warning_threshold * 1.5:
                return SLOStatus.WARNING
            else:
                return SLOStatus.CRITICAL
        elif target.slo_type in (SLOType.LATENCY_P50, SLOType.LATENCY_P90, SLOType.LATENCY_P95, SLOType.LATENCY_P99):
            if current_value <= target.target_value:
                return SLOStatus.HEALTHY
            elif target.warning_threshold and current_value <= target.warning_threshold * 1.5:
                return SLOStatus.WARNING
            else:
                return SLOStatus.CRITICAL
        else:
            # For availability, higher is better
            if current_value >= target.target_value:
                return SLOStatus.HEALTHY
            elif target.warning_threshold and current_value >= target.warning_threshold:
                return SLOStatus.WARNING
            else:
                return SLOStatus.CRITICAL

    def _calculate_error_budget(self, target: SLOTarget, current_value: float) -> float:
        """Calculate remaining error budget."""
        if target.slo_type == SLOType.AVAILABILITY:
            # Error budget = 1 - target (e.g., 0.1% for 99.9% availability)
            allowed_downtime = 1 - target.target_value
            actual_downtime = 1 - current_value
            if allowed_downtime == 0:
                return 1.0 if actual_downtime == 0 else 0.0
            return max(0, 1 - (actual_downtime / allowed_downtime))
        elif target.slo_type == SLOType.ERROR_RATE:
            if target.target_value == 0:
                return 1.0 if current_value == 0 else 0.0
            return max(0, 1 - (current_value / target.target_value))
        else:
            # For latency, calculate how much of budget is used
            if target.target_value == 0:
                return 1.0
            return max(0, 1 - (current_value / target.target_value))


# Convenience factory
def create_slo_monitor(
    config: SLOConfig | None = None,
    store: MetricsStore | None = None,
    alert_handler: AlertHandler | None = None,
) -> SLOMonitor:
    """Create an SLOMonitor with defaults."""
    return SLOMonitor(
        config=config or SLOConfig.default(),
        store=store or InMemoryMetricsStore(),
        alert_handler=alert_handler,
    )
