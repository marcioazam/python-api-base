"""api_composition enums."""

from enum import Enum


class ExecutionStrategy(Enum):
    """Execution strategies for API composition."""

    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    PARALLEL_WITH_FALLBACK = "parallel_with_fallback"

class CompositionStatus(Enum):
    """Status of a composition operation."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"  # Some calls succeeded
    FAILED = "failed"
