"""memory_profiler configuration."""

from dataclasses import dataclass


@dataclass
class MemoryProfilerConfig:
    """Configuration for memory profiler."""

    # Enable tracemalloc for detailed tracking
    enable_tracemalloc: bool = True
    # Number of frames to capture in traceback
    traceback_limit: int = 10
    # Memory thresholds (in MB)
    warning_threshold_mb: float = 500.0
    critical_threshold_mb: float = 1000.0
    # Growth rate threshold (MB per minute)
    growth_rate_threshold: float = 10.0
    # Leak detection window (minutes)
    leak_detection_window: int = 10
    # Minimum samples for leak detection
    min_samples_for_leak: int = 5
    # GC pressure threshold (collections per minute)
    gc_pressure_threshold: int = 100
    # Snapshot interval (seconds)
    snapshot_interval: int = 60
    # Max snapshots to retain
    max_snapshots: int = 1440  # 24 hours at 1/min
    # Top allocations to track
    top_allocations: int = 10
