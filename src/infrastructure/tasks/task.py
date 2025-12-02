"""Generic Task definition with PEP 695 generics.

**Feature: architecture-validation-fixes-2025**
**Validates: Requirements 23.1, 23.4, 23.5**
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from core.shared.utils.datetime import utc_now


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task execution priority."""

    LOW = 0
    NORMAL = 5
    HIGH = 10
    CRITICAL = 15


@dataclass(slots=True)
class TaskResult[TResult]:
    """Result of task execution.

    Type Parameters:
        TResult: The type of the result value.

    **Feature: architecture-validation-fixes-2025**
    **Validates: Requirements 23.5**
    """

    success: bool
    value: TResult | None = None
    error: str | None = None
    error_type: str | None = None
    execution_time_ms: float = 0.0


@dataclass
class Task[TPayload, TResult]:
    """Generic task definition for background processing.

    Type Parameters:
        TPayload: The type of the task payload/input.
        TResult: The type of the expected result.

    Example:
        >>> task: Task[EmailPayload, bool] = Task(
        ...     name="send_email",
        ...     payload=EmailPayload(to="user@example.com", subject="Hello"),
        ...     handler="email.send_email_handler",
        ... )

    **Feature: architecture-validation-fixes-2025**
    **Validates: Requirements 23.1, 23.4, 23.5**
    """

    name: str
    payload: TPayload
    handler: str

    # Identification
    task_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str | None = None

    # Status tracking
    status: TaskStatus = TaskStatus.PENDING
    result: TaskResult[TResult] | None = None

    # Timing
    created_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    scheduled_for: datetime | None = None

    # Retry state
    attempt: int = 0
    max_attempts: int = 3
    last_error: str | None = None

    # Priority and metadata
    priority: TaskPriority = TaskPriority.NORMAL
    queue_name: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)

    def mark_running(self) -> None:
        """Mark task as running."""
        self.status = TaskStatus.RUNNING
        self.started_at = utc_now()
        self.attempt += 1

    def mark_completed(self, result: TResult, execution_time_ms: float = 0.0) -> None:
        """Mark task as completed with result."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = utc_now()
        self.result = TaskResult(
            success=True,
            value=result,
            execution_time_ms=execution_time_ms,
        )

    def mark_failed(
        self, error: str, error_type: str = "Exception", execution_time_ms: float = 0.0
    ) -> None:
        """Mark task as failed."""
        self.last_error = error
        self.completed_at = utc_now()
        self.result = TaskResult(
            success=False,
            error=error,
            error_type=error_type,
            execution_time_ms=execution_time_ms,
        )

        if self.attempt < self.max_attempts:
            self.status = TaskStatus.RETRYING
        else:
            self.status = TaskStatus.FAILED

    def mark_cancelled(self) -> None:
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = utc_now()

    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.status == TaskStatus.RETRYING and self.attempt < self.max_attempts

    @property
    def is_terminal(self) -> bool:
        """Check if task is in terminal state."""
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize task to dictionary."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "handler": self.handler,
            "status": self.status.value,
            "priority": self.priority.value,
            "queue_name": self.queue_name,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "correlation_id": self.correlation_id,
            "last_error": self.last_error,
        }
