"""background_tasks enums."""

from enum import Enum


class TaskPriority(int, Enum):
    """Task priority levels."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
