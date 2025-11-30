"""memory_profiler service."""

import gc
import logging
import tracemalloc
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Any, Protocol, runtime_checkable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .config import MemoryProfilerConfig
from .enums import MemoryAlertSeverity, MemoryAlertType
from .models import AllocationInfo, MemoryAlert

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MemorySnapshot:
    """A snapshot of memory state."""

    timestamp: datetime
    rss_bytes: int  # Resident Set Size
    vms_bytes: int  # Virtual Memory Size
    heap_bytes: int  # Heap allocation
    gc_objects: int  # Number of tracked objects
    gc_collections: tuple[int, int, int]  # Gen 0, 1, 2 collections

    @property
    def rss_mb(self) -> float:
        """RSS in megabytes."""
        return self.rss_bytes / (1024 * 1024)

    @property
    def vms_mb(self) -> float:
        """VMS in megabytes."""
        return self.vms_bytes / (1024 * 1024)

    @property
    def heap_mb(self) -> float:
        """Heap in megabytes."""
        return self.heap_bytes / (1024 * 1024)

@runtime_checkable
class MemoryAlertHandler(Protocol):
    """Protocol for handling memory alerts."""

    async def handle(self, alert: MemoryAlert) -> None: ...

class LogMemoryAlertHandler:
    """Handler that logs memory alerts using Python logging."""

    SEVERITY_MAP: dict[MemoryAlertSeverity, int] = {
        MemoryAlertSeverity.CRITICAL: logging.ERROR,
        MemoryAlertSeverity.WARNING: logging.WARNING,
        MemoryAlertSeverity.INFO: logging.INFO,
    }

    async def handle(self, alert: MemoryAlert) -> None:
        """Log the memory alert with appropriate severity level."""
        level = self.SEVERITY_MAP.get(alert.severity, logging.WARNING)
        logger.log(
            level,
            "Memory alert: %s - %s (current: %.2f, threshold: %.2f)",
            alert.alert_type.value,
            alert.message,
            alert.current_value,
            alert.threshold,
        )

class MemoryProfiler:
    """Memory profiler for tracking and analyzing memory usage."""

    def __init__(
        self,
        config: MemoryProfilerConfig | None = None,
        handler: MemoryAlertHandler | None = None,
    ) -> None:
        self._config = config or MemoryProfilerConfig()
        self._handler = handler or LogMemoryAlertHandler()
        self._snapshots: list[MemorySnapshot] = []
        self._last_gc_counts: tuple[int, int, int] = (0, 0, 0)
        self._started = False

    def start(self) -> None:
        """Start memory profiling."""
        if self._started:
            return
        if self._config.enable_tracemalloc and not tracemalloc.is_tracing():
            tracemalloc.start(self._config.traceback_limit)
        self._last_gc_counts = tuple(gc.get_count())  # type: ignore[assignment]
        self._started = True

    def stop(self) -> None:
        """Stop memory profiling."""
        if not self._started:
            return
        if self._config.enable_tracemalloc and tracemalloc.is_tracing():
            tracemalloc.stop()
        self._started = False

    def take_snapshot(self) -> MemorySnapshot:
        """Take a memory snapshot."""
        try:
            import psutil
            process = psutil.Process()
            mem_info = process.memory_info()
            rss = mem_info.rss
            vms = mem_info.vms
        except ImportError:
            rss = 0
            vms = 0

        heap = 0
        if tracemalloc.is_tracing():
            current, _ = tracemalloc.get_traced_memory()
            heap = current

        snapshot = MemorySnapshot(
            timestamp=datetime.now(UTC),
            rss_bytes=rss,
            vms_bytes=vms,
            heap_bytes=heap,
            gc_objects=len(gc.get_objects()),
            gc_collections=tuple(gc.get_count()),  # type: ignore[arg-type]
        )

        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._config.max_snapshots:
            self._snapshots = self._snapshots[-self._config.max_snapshots:]

        return snapshot

    async def analyze(self) -> list[MemoryAlert]:
        """Analyze memory state and return any alerts."""
        alerts: list[MemoryAlert] = []

        if not self._snapshots:
            self.take_snapshot()

        latest = self._snapshots[-1]

        # Check high memory usage
        if latest.rss_mb >= self._config.critical_threshold_mb:
            alert = MemoryAlert(
                alert_type=MemoryAlertType.HIGH_USAGE,
                severity=MemoryAlertSeverity.CRITICAL,
                message=f"Critical memory usage: {latest.rss_mb:.1f} MB",
                current_value=latest.rss_mb,
                threshold=self._config.critical_threshold_mb,
                timestamp=latest.timestamp,
            )
            alerts.append(alert)
            await self._handler.handle(alert)
        elif latest.rss_mb >= self._config.warning_threshold_mb:
            alert = MemoryAlert(
                alert_type=MemoryAlertType.HIGH_USAGE,
                severity=MemoryAlertSeverity.WARNING,
                message=f"High memory usage: {latest.rss_mb:.1f} MB",
                current_value=latest.rss_mb,
                threshold=self._config.warning_threshold_mb,
                timestamp=latest.timestamp,
            )
            alerts.append(alert)
            await self._handler.handle(alert)

        # Check for memory leak
        leak_alert = self._detect_leak()
        if leak_alert:
            alerts.append(leak_alert)
            await self._handler.handle(leak_alert)

        # Check GC pressure
        gc_alert = self._check_gc_pressure()
        if gc_alert:
            alerts.append(gc_alert)
            await self._handler.handle(gc_alert)

        return alerts

    def _detect_leak(self) -> MemoryAlert | None:
        """Detect potential memory leaks."""
        if len(self._snapshots) < self._config.min_samples_for_leak:
            return None

        window = timedelta(minutes=self._config.leak_detection_window)
        cutoff = datetime.now(UTC) - window
        recent = [s for s in self._snapshots if s.timestamp > cutoff]

        if len(recent) < self._config.min_samples_for_leak:
            return None

        # Calculate growth rate
        first = recent[0]
        last = recent[-1]
        time_diff = (last.timestamp - first.timestamp).total_seconds() / 60  # minutes

        if time_diff <= 0:
            return None

        growth_mb = last.rss_mb - first.rss_mb
        growth_rate = growth_mb / time_diff  # MB per minute

        if growth_rate > self._config.growth_rate_threshold:
            return MemoryAlert(
                alert_type=MemoryAlertType.LEAK_DETECTED,
                severity=MemoryAlertSeverity.WARNING,
                message=f"Potential memory leak: {growth_rate:.2f} MB/min growth",
                current_value=growth_rate,
                threshold=self._config.growth_rate_threshold,
                timestamp=last.timestamp,
                details={
                    "start_mb": first.rss_mb,
                    "end_mb": last.rss_mb,
                    "duration_minutes": time_diff,
                },
            )
        return None

    def _check_gc_pressure(self) -> MemoryAlert | None:
        """Check for GC pressure."""
        current_counts = gc.get_count()
        if not self._last_gc_counts:
            self._last_gc_counts = current_counts
            return None

        total_collections = sum(current_counts) - sum(self._last_gc_counts)
        self._last_gc_counts = current_counts

        if total_collections > self._config.gc_pressure_threshold:
            return MemoryAlert(
                alert_type=MemoryAlertType.GC_PRESSURE,
                severity=MemoryAlertSeverity.WARNING,
                message=f"High GC pressure: {total_collections} collections",
                current_value=float(total_collections),
                threshold=float(self._config.gc_pressure_threshold),
                timestamp=datetime.now(UTC),
                details={"gen0": current_counts[0], "gen1": current_counts[1], "gen2": current_counts[2]},
            )
        return None

    def get_top_allocations(self) -> list[AllocationInfo]:
        """Get top memory allocations."""
        if not tracemalloc.is_tracing():
            return []

        snapshot = tracemalloc.take_snapshot()
        stats = snapshot.statistics("traceback")

        result = []
        for stat in stats[:self._config.top_allocations]:
            tb_lines = [str(line) for line in stat.traceback.format()]
            result.append(AllocationInfo(
                size_bytes=stat.size,
                count=stat.count,
                traceback=tb_lines,
            ))
        return result

    def get_statistics(self) -> dict[str, Any]:
        """Get memory statistics."""
        if not self._snapshots:
            return {"error": "No snapshots available"}

        latest = self._snapshots[-1]
        rss_values = [s.rss_mb for s in self._snapshots]

        return {
            "current_rss_mb": latest.rss_mb,
            "current_vms_mb": latest.vms_mb,
            "current_heap_mb": latest.heap_mb,
            "gc_objects": latest.gc_objects,
            "gc_collections": latest.gc_collections,
            "min_rss_mb": min(rss_values),
            "max_rss_mb": max(rss_values),
            "avg_rss_mb": sum(rss_values) / len(rss_values),
            "snapshot_count": len(self._snapshots),
        }

    def force_gc(self) -> dict[str, int]:
        """Force garbage collection and return stats."""
        before = len(gc.get_objects())
        collected = gc.collect()
        after = len(gc.get_objects())
        return {
            "collected": collected,
            "objects_before": before,
            "objects_after": after,
            "freed": before - after,
        }

class MemoryProfilerMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic memory profiling per request."""

    def __init__(
        self,
        app: Any,
        profiler: MemoryProfiler | None = None,
        track_per_request: bool = False,
        analyze_interval: int = 100,  # Analyze every N requests
    ) -> None:
        super().__init__(app)
        self._profiler = profiler or MemoryProfiler()
        self._track_per_request = track_per_request
        self._analyze_interval = analyze_interval
        self._request_count = 0
        self._profiler.start()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request with memory tracking."""
        self._request_count += 1

        before_snapshot = None
        if self._track_per_request:
            before_snapshot = self._profiler.take_snapshot()

        response = await call_next(request)

        if self._track_per_request and before_snapshot:
            after_snapshot = self._profiler.take_snapshot()
            memory_delta = after_snapshot.rss_bytes - before_snapshot.rss_bytes
            response.headers["X-Memory-Delta-Bytes"] = str(memory_delta)

        # Periodic analysis
        if self._request_count % self._analyze_interval == 0:
            self._profiler.take_snapshot()
            await self._profiler.analyze()

        return response

    @property
    def profiler(self) -> MemoryProfiler:
        """Get the underlying profiler."""
        return self._profiler

def create_memory_profiler(
    config: MemoryProfilerConfig | None = None,
    handler: MemoryAlertHandler | None = None,
) -> MemoryProfiler:
    """Create a MemoryProfiler with defaults."""
    return MemoryProfiler(config=config, handler=handler)

def create_memory_middleware(
    app: Any,
    config: MemoryProfilerConfig | None = None,
    track_per_request: bool = False,
    analyze_interval: int = 100,
) -> MemoryProfilerMiddleware:
    """Create memory profiler middleware."""
    profiler = create_memory_profiler(config=config)
    return MemoryProfilerMiddleware(
        app=app,
        profiler=profiler,
        track_per_request=track_per_request,
        analyze_interval=analyze_interval,
    )
