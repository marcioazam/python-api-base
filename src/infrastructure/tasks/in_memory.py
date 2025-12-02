"""In-memory task queue implementation with PEP 695 generics.

**Feature: architecture-validation-fixes-2025**
**Validates: Requirements 23.1, 23.2, 23.5**
"""

import asyncio
import logging
import time
from collections.abc import Sequence

from infrastructure.tasks.task import Task, TaskResult, TaskStatus
from infrastructure.tasks.protocols import TaskHandler
from infrastructure.tasks.retry import RetryPolicy, DEFAULT_RETRY_POLICY

logger = logging.getLogger(__name__)


class InMemoryTaskQueue[TPayload, TResult]:
    """In-memory task queue implementation.

    Suitable for development, testing, and single-instance deployments.
    For production with multiple workers, use Redis/Celery based implementations.

    Type Parameters:
        TPayload: The type of task payloads.
        TResult: The type of task results.

    Example:
        >>> queue: InMemoryTaskQueue[EmailPayload, bool] = InMemoryTaskQueue()
        >>> task = Task(name="send_email", payload=payload, handler="email.send")
        >>> await queue.enqueue(task)
        >>> await queue.process_next(handlers)

    **Feature: architecture-validation-fixes-2025**
    **Validates: Requirements 23.1, 23.2, 23.5**
    """

    def __init__(
        self,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        """Initialize in-memory task queue.

        Args:
            retry_policy: Policy for retry delays.
        """
        self._tasks: dict[str, Task[TPayload, TResult]] = {}
        self._queue: asyncio.PriorityQueue[tuple[int, float, str]] = (
            asyncio.PriorityQueue()
        )
        self._retry_policy = retry_policy or DEFAULT_RETRY_POLICY
        self._handlers: dict[str, TaskHandler[TPayload, TResult]] = {}
        self._lock = asyncio.Lock()

    def register_handler(
        self, name: str, handler: TaskHandler[TPayload, TResult]
    ) -> None:
        """Register a task handler.

        Args:
            name: Handler name (matches task.handler field).
            handler: Handler implementation.
        """
        self._handlers[name] = handler

    async def enqueue(self, task: Task[TPayload, TResult]) -> str:
        """Add a task to the queue.

        Args:
            task: Task to enqueue.

        Returns:
            Task ID.
        """
        async with self._lock:
            self._tasks[task.task_id] = task

            # Priority queue: lower number = higher priority
            # Negate priority so HIGH (10) comes before LOW (0)
            priority = -task.priority.value
            timestamp = time.time()

            await self._queue.put((priority, timestamp, task.task_id))

            logger.info(
                f"Task enqueued: {task.task_id}",
                extra={
                    "task_id": task.task_id,
                    "task_name": task.name,
                    "queue": task.queue_name,
                    "priority": task.priority.value,
                },
            )

        return task.task_id

    async def dequeue(self) -> Task[TPayload, TResult] | None:
        """Get next task from queue.

        Returns:
            Next pending task or None if queue is empty.
        """
        try:
            _, _, task_id = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            task = self._tasks.get(task_id)

            if task and task.status == TaskStatus.PENDING:
                return task
            return None
        except asyncio.TimeoutError:
            return None

    async def get_task(self, task_id: str) -> Task[TPayload, TResult] | None:
        """Get task by ID."""
        return self._tasks.get(task_id)

    async def update_task(self, task: Task[TPayload, TResult]) -> None:
        """Update task state."""
        async with self._lock:
            self._tasks[task.task_id] = task

    async def get_tasks_by_status(
        self, status: TaskStatus, limit: int = 100
    ) -> Sequence[Task[TPayload, TResult]]:
        """Get tasks by status."""
        return [
            task for task in list(self._tasks.values())[:limit] if task.status == status
        ]

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.mark_cancelled()
            return True
        return False

    async def retry_task(self, task_id: str) -> bool:
        """Retry a failed task."""
        task = self._tasks.get(task_id)
        if task and task.can_retry:
            task.status = TaskStatus.PENDING
            await self.enqueue(task)
            return True
        return False

    async def process_next(
        self,
        handlers: dict[str, TaskHandler[TPayload, TResult]] | None = None,
    ) -> TaskResult[TResult] | None:
        """Process the next task in queue.

        Args:
            handlers: Optional handler overrides.

        Returns:
            Task result or None if no task available.

        **Feature: architecture-validation-fixes-2025**
        **Validates: Requirements 23.3, 23.4**
        """
        task = await self.dequeue()
        if not task:
            return None

        available_handlers = handlers or self._handlers
        handler = available_handlers.get(task.handler)

        if not handler:
            logger.error(
                f"No handler registered for: {task.handler}",
                extra={
                    "task_id": task.task_id,
                    "handler": task.handler,
                    "correlation_id": task.correlation_id,
                },
            )
            task.mark_failed(f"Handler not found: {task.handler}", "HandlerNotFound")
            await self.update_task(task)
            return task.result

        task.mark_running()
        await self.update_task(task)

        start_time = time.perf_counter()
        try:
            result = await handler.handle(task.payload)
            execution_time = (time.perf_counter() - start_time) * 1000
            task.mark_completed(result, execution_time)

            logger.info(
                f"Task completed: {task.task_id}",
                extra={
                    "task_id": task.task_id,
                    "task_name": task.name,
                    "execution_time_ms": execution_time,
                    "correlation_id": task.correlation_id,
                },
            )

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            task.mark_failed(str(e), type(e).__name__, execution_time)

            logger.error(
                f"Task failed: {task.task_id}",
                extra={
                    "task_id": task.task_id,
                    "task_name": task.name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "attempt": task.attempt,
                    "max_attempts": task.max_attempts,
                    "correlation_id": task.correlation_id,
                },
                exc_info=True,
            )

            # Schedule retry if applicable
            if task.can_retry:
                delay = self._retry_policy.get_delay(task.attempt)
                logger.info(
                    f"Scheduling retry for task {task.task_id} in {delay:.1f}s",
                    extra={
                        "task_id": task.task_id,
                        "attempt": task.attempt,
                        "delay_seconds": delay,
                    },
                )
                await asyncio.sleep(delay)
                task.status = TaskStatus.PENDING
                await self.enqueue(task)

        await self.update_task(task)
        return task.result

    async def process_all(
        self,
        handlers: dict[str, TaskHandler[TPayload, TResult]] | None = None,
        max_tasks: int = 100,
    ) -> int:
        """Process all pending tasks.

        Args:
            handlers: Optional handler overrides.
            max_tasks: Maximum tasks to process.

        Returns:
            Number of tasks processed.
        """
        processed = 0
        while processed < max_tasks:
            result = await self.process_next(handlers)
            if result is None:
                break
            processed += 1
        return processed

    @property
    def pending_count(self) -> int:
        """Get count of pending tasks."""
        return sum(
            1 for task in self._tasks.values() if task.status == TaskStatus.PENDING
        )

    @property
    def total_count(self) -> int:
        """Get total task count."""
        return len(self._tasks)

    def clear(self) -> None:
        """Clear all tasks (for testing)."""
        self._tasks.clear()
        self._queue = asyncio.PriorityQueue()
