"""Async background task queue with priorities and retries.

**Feature: api-architecture-analysis, Task 12.5: Async Background Tasks**
**Validates: Requirements 6.2, 9.4**

Provides background task execution with scheduling, priorities, and retries.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


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
class TaskResult(Generic[T]):
    """Task execution result.

    Attributes:
        task_id: Task identifier.
        status: Execution status.
        result: Task result if successful.
        error: Error message if failed.
        attempts: Number of execution attempts.
        started_at: Execution start time.
        completed_at: Execution completion time.
        duration_ms: Execution duration in milliseconds.
    """

    task_id: str
    status: TaskStatus
    result: T | None = None
    error: str | None = None
    attempts: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float = 0.0


@dataclass
class Task(Generic[T]):
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
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    scheduled_at: datetime | None = None
    result: TaskResult[T] | None = None

    def __lt__(self, other: "Task") -> bool:
        """Compare tasks by priority for queue ordering."""
        return self.config.priority.value > other.config.priority.value


class QueueStats(BaseModel):
    """Task queue statistics.

    Attributes:
        total_tasks: Total tasks submitted.
        pending_tasks: Tasks waiting to execute.
        running_tasks: Currently executing tasks.
        completed_tasks: Successfully completed tasks.
        failed_tasks: Failed tasks.
        avg_execution_time_ms: Average execution time.
    """

    total_tasks: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_execution_time_ms: float = 0.0


class BackgroundTaskQueue:
    """Background task queue with priorities and retries.

    Provides async task execution with:
    - Priority-based scheduling
    - Automatic retries with backoff
    - Task timeout handling
    - Statistics tracking
    """

    def __init__(
        self,
        max_workers: int = 5,
        default_config: TaskConfig | None = None,
    ) -> None:
        """Initialize task queue.

        Args:
            max_workers: Maximum concurrent workers.
            default_config: Default task configuration.
        """
        self._max_workers = max_workers
        self._default_config = default_config or TaskConfig()
        self._tasks: dict[str, Task] = {}
        self._queue: asyncio.PriorityQueue[Task] = asyncio.PriorityQueue()
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._stats = QueueStats()
        self._execution_times: list[float] = []

    async def start(self) -> None:
        """Start the task queue workers."""
        if self._running:
            return

        self._running = True
        for i in range(self._max_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self._workers.append(worker)

    async def stop(self, wait: bool = True) -> None:
        """Stop the task queue.

        Args:
            wait: Whether to wait for pending tasks.
        """
        self._running = False

        if wait:
            # Wait for queue to empty
            while not self._queue.empty():
                await asyncio.sleep(0.1)

        # Cancel workers
        for worker in self._workers:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass

        self._workers.clear()

    async def submit(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        config: TaskConfig | None = None,
        scheduled_at: datetime | None = None,
        **kwargs: Any,
    ) -> str:
        """Submit a task for execution.

        Args:
            func: Async function to execute.
            *args: Function arguments.
            config: Task configuration.
            scheduled_at: Scheduled execution time.
            **kwargs: Function keyword arguments.

        Returns:
            Task ID.
        """
        task_id = str(uuid.uuid4())
        task: Task[T] = Task(
            id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            config=config or self._default_config,
            scheduled_at=scheduled_at,
        )

        self._tasks[task_id] = task
        self._stats.total_tasks += 1
        self._stats.pending_tasks += 1

        await self._queue.put(task)
        return task_id

    async def schedule(
        self,
        func: Callable[..., Awaitable[T]],
        delay_ms: int,
        *args: Any,
        config: TaskConfig | None = None,
        **kwargs: Any,
    ) -> str:
        """Schedule a task for delayed execution.

        Args:
            func: Async function to execute.
            delay_ms: Delay in milliseconds.
            *args: Function arguments.
            config: Task configuration.
            **kwargs: Function keyword arguments.

        Returns:
            Task ID.
        """
        scheduled_at = datetime.now(timezone.utc) + timedelta(milliseconds=delay_ms)
        return await self.submit(
            func, *args, config=config, scheduled_at=scheduled_at, **kwargs
        )

    async def cancel(self, task_id: str) -> bool:
        """Cancel a pending task.

        Args:
            task_id: Task ID to cancel.

        Returns:
            True if cancelled, False if not found or already running.
        """
        if task_id not in self._tasks:
            return False

        task = self._tasks[task_id]
        if task.status != TaskStatus.PENDING:
            return False

        task.status = TaskStatus.CANCELLED
        self._stats.pending_tasks -= 1
        return True

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID.

        Args:
            task_id: Task ID.

        Returns:
            Task or None if not found.
        """
        return self._tasks.get(task_id)

    def get_result(self, task_id: str) -> TaskResult | None:
        """Get task result.

        Args:
            task_id: Task ID.

        Returns:
            Task result or None.
        """
        task = self._tasks.get(task_id)
        return task.result if task else None

    async def wait_for(self, task_id: str, timeout: float | None = None) -> TaskResult | None:
        """Wait for task completion.

        Args:
            task_id: Task ID.
            timeout: Maximum wait time in seconds.

        Returns:
            Task result or None if timeout.
        """
        start = asyncio.get_event_loop().time()

        while True:
            task = self._tasks.get(task_id)
            if not task:
                return None

            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return task.result

            if timeout and (asyncio.get_event_loop().time() - start) > timeout:
                return None

            await asyncio.sleep(0.1)

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker loop for processing tasks.

        Args:
            worker_id: Worker identifier.
        """
        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if task.status == TaskStatus.CANCELLED:
                continue

            # Check scheduled time
            if task.scheduled_at and datetime.now(timezone.utc) < task.scheduled_at:
                await self._queue.put(task)
                await asyncio.sleep(0.1)
                continue

            await self._execute_task(task)

    async def _execute_task(self, task: Task) -> None:
        """Execute a task with retry handling.

        Args:
            task: Task to execute.
        """
        task.status = TaskStatus.RUNNING
        self._stats.pending_tasks -= 1
        self._stats.running_tasks += 1

        started_at = datetime.now(timezone.utc)
        task.attempts += 1

        try:
            # Execute with timeout
            timeout_seconds = task.config.timeout_ms / 1000
            result = await asyncio.wait_for(
                task.func(*task.args, **task.kwargs),
                timeout=timeout_seconds,
            )

            completed_at = datetime.now(timezone.utc)
            duration_ms = (completed_at - started_at).total_seconds() * 1000

            task.status = TaskStatus.COMPLETED
            task.result = TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                result=result,
                attempts=task.attempts,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
            )

            self._stats.running_tasks -= 1
            self._stats.completed_tasks += 1
            self._execution_times.append(duration_ms)
            if len(self._execution_times) > 100:
                self._execution_times.pop(0)
            self._stats.avg_execution_time_ms = (
                sum(self._execution_times) / len(self._execution_times)
            )

        except Exception as e:
            # Handle failure
            if task.attempts < task.config.max_retries:
                # Retry
                task.status = TaskStatus.RETRYING
                delay = task.config.retry_delay_ms * (
                    task.config.retry_backoff ** (task.attempts - 1)
                )
                await asyncio.sleep(delay / 1000)
                task.status = TaskStatus.PENDING
                self._stats.running_tasks -= 1
                self._stats.pending_tasks += 1
                await self._queue.put(task)
            else:
                # Final failure
                completed_at = datetime.now(timezone.utc)
                duration_ms = (completed_at - started_at).total_seconds() * 1000

                task.status = TaskStatus.FAILED
                task.result = TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error=str(e),
                    attempts=task.attempts,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=duration_ms,
                )

                self._stats.running_tasks -= 1
                self._stats.failed_tasks += 1

    def get_stats(self) -> QueueStats:
        """Get queue statistics.

        Returns:
            Current statistics.
        """
        return self._stats.model_copy()

    @property
    def is_running(self) -> bool:
        """Check if queue is running."""
        return self._running

    @property
    def pending_count(self) -> int:
        """Get number of pending tasks."""
        return self._stats.pending_tasks
