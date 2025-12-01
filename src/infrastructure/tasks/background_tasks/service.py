"""Background task queue service.

**Feature: full-codebase-review-2025, Task 1.5: Refactor background_tasks**
**Validates: Requirements 9.2**
"""

import asyncio
import logging
import traceback
import uuid
from datetime import datetime, timedelta, UTC
from typing import Any
from collections.abc import Awaitable, Callable

from .config import TaskConfig
from .enums import TaskStatus
from .models import Task, TaskResult
from .stats import QueueStats

logger = logging.getLogger(__name__)


class BackgroundTaskQueue:
    """Background task queue with priorities and retries."""

    def __init__(
        self,
        max_workers: int = 5,
        default_config: TaskConfig | None = None,
    ) -> None:
        """Initialize task queue."""
        self._max_workers = max_workers
        self._default_config = default_config or TaskConfig()
        self._tasks: dict[str, Task] = {}
        self._queue: asyncio.PriorityQueue[Task] = asyncio.PriorityQueue()
        self._workers: list[asyncio.Task[None]] = []
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
        """Stop the task queue."""
        self._running = False
        if wait:
            while not self._queue.empty():
                await asyncio.sleep(0.1)
        for worker in self._workers:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
        self._workers.clear()

    async def submit[T](
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        config: TaskConfig | None = None,
        scheduled_at: datetime | None = None,
        **kwargs: Any,
    ) -> str:
        """Submit a task for execution."""
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

    async def schedule[T](
        self,
        func: Callable[..., Awaitable[T]],
        delay_ms: int,
        *args: Any,
        config: TaskConfig | None = None,
        **kwargs: Any,
    ) -> str:
        """Schedule a task for delayed execution."""
        scheduled_at = datetime.now(UTC) + timedelta(milliseconds=delay_ms)
        return await self.submit(func, *args, config=config, scheduled_at=scheduled_at, **kwargs)

    async def cancel(self, task_id: str) -> bool:
        """Cancel a pending task."""
        if task_id not in self._tasks:
            return False
        task = self._tasks[task_id]
        if task.status != TaskStatus.PENDING:
            return False
        task.status = TaskStatus.CANCELLED
        self._stats.pending_tasks -= 1
        return True

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def get_result(self, task_id: str) -> TaskResult | None:
        """Get task result."""
        task = self._tasks.get(task_id)
        return task.result if task else None

    async def wait_for(self, task_id: str, timeout: float | None = None) -> TaskResult | None:
        """Wait for task completion."""
        start = asyncio.get_running_loop().time()
        while True:
            task = self._tasks.get(task_id)
            if not task:
                return None
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return task.result
            if timeout and (asyncio.get_running_loop().time() - start) > timeout:
                return None
            await asyncio.sleep(0.1)

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker loop for processing tasks."""
        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            if task.status == TaskStatus.CANCELLED:
                continue
            if task.scheduled_at and datetime.now(UTC) < task.scheduled_at:
                await self._queue.put(task)
                await asyncio.sleep(0.1)
                continue
            await self._execute_task(task)

    async def _execute_task(self, task: Task) -> None:
        """Execute a task with retry handling."""
        task.status = TaskStatus.RUNNING
        self._stats.pending_tasks -= 1
        self._stats.running_tasks += 1
        started_at = datetime.now(UTC)
        task.attempts += 1

        try:
            timeout_seconds = task.config.timeout_ms / 1000
            result = await asyncio.wait_for(
                task.func(*task.args, **task.kwargs), timeout=timeout_seconds
            )
            self._complete_task(task, result, started_at)
        except asyncio.CancelledError:
            self._stats.running_tasks -= 1
            raise
        except asyncio.TimeoutError as e:
            await self._handle_failure(task, e, "TimeoutError", started_at)
        except Exception as e:
            await self._handle_failure(task, e, type(e).__name__, started_at, traceback.format_exc())

    def _complete_task(self, task: Task, result: Any, started_at: datetime) -> None:
        """Mark task as completed."""
        completed_at = datetime.now(UTC)
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
        self._update_execution_time(duration_ms)

    def _update_execution_time(self, duration_ms: float) -> None:
        """Update average execution time."""
        self._execution_times.append(duration_ms)
        if len(self._execution_times) > 100:
            self._execution_times.pop(0)
        self._stats.avg_execution_time_ms = sum(self._execution_times) / len(self._execution_times)

    async def _handle_failure(
        self,
        task: Task,
        error: Exception,
        error_type: str,
        started_at: datetime,
        stack_trace: str | None = None,
    ) -> None:
        """Handle task failure with retry logic."""
        completed_at = datetime.now(UTC)
        duration_ms = (completed_at - started_at).total_seconds() * 1000
        logger.warning("Task failed", extra={"task_id": task.id, "attempt": task.attempts, "error_type": error_type})

        if task.attempts < task.config.max_retries:
            task.status = TaskStatus.RETRYING
            delay = task.config.retry_delay_ms * (task.config.retry_backoff ** (task.attempts - 1))
            await asyncio.sleep(delay / 1000)
            task.status = TaskStatus.PENDING
            self._stats.running_tasks -= 1
            self._stats.pending_tasks += 1
            await self._queue.put(task)
        else:
            task.status = TaskStatus.FAILED
            task.result = TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(error),
                error_type=error_type,
                stack_trace=stack_trace,
                attempts=task.attempts,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
            )
            self._stats.running_tasks -= 1
            self._stats.failed_tasks += 1

    def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        return self._stats.model_copy()

    @property
    def is_running(self) -> bool:
        """Check if queue is running."""
        return self._running

    @property
    def pending_count(self) -> int:
        """Get number of pending tasks."""
        return self._stats.pending_tasks
