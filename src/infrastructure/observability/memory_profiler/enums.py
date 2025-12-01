"""memory_profiler enums.

**Feature: shared-modules-phase3-fixes, Task 5.1**
"""

from enum import Enum


class MemoryAlertSeverity(Enum):
    """Severity levels for memory alerts."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class MemoryAlertType(Enum):
    """Types of memory alerts."""

    HIGH_USAGE = "high_usage"
    LEAK_DETECTED = "leak_detected"
    GROWTH_RATE = "growth_rate"
    ALLOCATION_SPIKE = "allocation_spike"
    GC_PRESSURE = "gc_pressure"
