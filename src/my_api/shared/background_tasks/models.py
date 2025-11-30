"""background_tasks models."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
from collections.abc import Awaitable, Callable

from .enums import TaskPriority, TaskStatus


@dataclass
class TaskConfig:
    """Task configuration.

    Attributes:
        max_retries: Maximum retry attempts.
        retry_delay_ms: Initial retry delay in milliseconds.
        retry_backoff: Backoff multiplier for retries.
        timeout_ms: Task timeout in milliseconds.
        priority: Task priority.
    """

    max_retries: int = 3
    retry_delay_ms: int = 1000
    retry_backoff: float = 2.0
    timeout_ms: int = 30000
    priority: TaskPriority = TaskPriority.NORMAL


@dataclass
class TaskResult[T]:
    """Task execution result.

    Attributes:
        task_id: Task identifier.
        status: Execution status.
        result: Task result if successful.
        error: Error message if failed.
        error_type: Exception class name if failed.
        stack_trace: Full traceback if failed.
        attempts: Number of execution attempts.
        started_at: Execution start time.
        completed_at: Execution completion time.
        duration_ms: Execution duration in milliseconds.
    """

    task_id: str
    status: TaskStatus
    result: T | None = None
    error: str | None = None
    error_type: str | None = None
    stack_trace: str | None = None
    attempts: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float = 0.0

@dataclass
class Task[T]:
    """Background task.

    Attributes:
        id: Task identifier.
        func: Async function to execute.
        args: Function arguments.
        kwargs: Function keyword arguments.
        config: Task configuration.
        status: Current status.
        attempts: Execution attempts.
        created_at: Creation time.
        scheduled_at: Scheduled execution time.
        result: Execution result.
    """

    id: str
    func: Callable[..., Awaitable[T]]
    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    config: TaskConfig = field(default_factory=TaskConfig)
    status: TaskStatus = TaskStatus.PENDING
    attempts: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    scheduled_at: datetime | None = None
    result: TaskResult[T] | None = None

    def __lt__(self, other: "Task") -> bool:
        """Compare tasks by priority for queue ordering."""
        return self.config.priority.value > other.config.priority.value
