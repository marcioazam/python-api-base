"""Task Queue protocols with PEP 695 generics.

**Feature: architecture-validation-fixes-2025**
**Validates: Requirements 23.1, 23.2, 23.3**
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from infrastructure.tasks.task import Task, TaskStatus


@runtime_checkable
class TaskHandler[TPayload, TResult](Protocol):
    """Protocol for task handlers.

    Type Parameters:
        TPayload: The type of the task payload/input.
        TResult: The type of the expected result.

    **Feature: architecture-validation-fixes-2025**
    **Validates: Requirements 23.1**
    """

    async def handle(self, payload: TPayload) -> TResult:
        """Execute the task with given payload.

        Args:
            payload: Task input data.

        Returns:
            Task result.

        Raises:
            Exception: On task failure.
        """
        ...


@runtime_checkable
class TaskQueue[TPayload, TResult](Protocol):
    """Protocol for task queue implementations.

    Type Parameters:
        TPayload: The type of task payloads.
        TResult: The type of task results.

    **Feature: architecture-validation-fixes-2025**
    **Validates: Requirements 23.2**
    """

    async def enqueue(
        self,
        task: Task[TPayload, TResult],
    ) -> str:
        """Add a task to the queue.

        Args:
            task: Task to enqueue.

        Returns:
            Task ID.
        """
        ...

    async def dequeue(self) -> Task[TPayload, TResult] | None:
        """Get next task from queue.

        Returns:
            Next pending task or None if queue is empty.
        """
        ...

    async def get_task(self, task_id: str) -> Task[TPayload, TResult] | None:
        """Get task by ID.

        Args:
            task_id: Task identifier.

        Returns:
            Task if found, None otherwise.
        """
        ...

    async def update_task(self, task: Task[TPayload, TResult]) -> None:
        """Update task state.

        Args:
            task: Task with updated state.
        """
        ...

    async def get_tasks_by_status(
        self, status: TaskStatus, limit: int = 100
    ) -> Sequence[Task[TPayload, TResult]]:
        """Get tasks by status.

        Args:
            status: Task status to filter by.
            limit: Maximum tasks to return.

        Returns:
            Sequence of matching tasks.
        """
        ...

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task.

        Args:
            task_id: Task identifier.

        Returns:
            True if cancelled, False if not found or already running.
        """
        ...

    async def retry_task(self, task_id: str) -> bool:
        """Retry a failed task.

        Args:
            task_id: Task identifier.

        Returns:
            True if requeued for retry.
        """
        ...


@runtime_checkable
class TaskScheduler(Protocol):
    """Protocol for scheduling delayed/recurring tasks.

    **Feature: architecture-validation-fixes-2025**
    **Validates: Requirements 23.2**
    """

    async def schedule(
        self,
        task: Task,
        run_at: datetime,
    ) -> str:
        """Schedule a task for future execution.

        Args:
            task: Task to schedule.
            run_at: When to execute the task.

        Returns:
            Task ID.
        """
        ...

    async def schedule_recurring(
        self,
        task: Task,
        cron_expression: str,
    ) -> str:
        """Schedule a recurring task.

        Args:
            task: Task template.
            cron_expression: Cron schedule expression.

        Returns:
            Schedule ID.
        """
        ...

    async def cancel_schedule(self, schedule_id: str) -> bool:
        """Cancel a scheduled task.

        Args:
            schedule_id: Schedule identifier.

        Returns:
            True if cancelled.
        """
        ...
