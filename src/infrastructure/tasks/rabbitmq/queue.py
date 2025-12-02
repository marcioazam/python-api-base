"""RabbitMQ task queue implementation.

**Feature: enterprise-generics-2025**
**Requirement: R3.1 - Generic_TaskQueue[TTask, TResult]**
**Refactored: 2025 - Extracted from rabbitmq.py for SRP compliance**
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from infrastructure.tasks.rabbitmq.config import RabbitMQConfig
from infrastructure.tasks.task import TaskResult, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class TaskHandle[TTask: BaseModel, TResult]:
    """Handle for tracking enqueued task.

    **Requirement: R3.2 - TaskHandle[TTask, TResult] with task ID**

    Type Parameters:
        TTask: Task payload type.
        TResult: Expected result type.
    """

    task_id: str
    task: TTask
    queue: RabbitMQTaskQueue[TTask, TResult]
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    async def result(self, timeout: timedelta | None = None) -> TResult:
        """Wait for and return task result.

        **Requirement: R3.4 - TaskHandle.result() returns TResult**
        """
        return await self.queue.get_result(self.task_id, timeout)

    async def status(self) -> TaskStatus:
        """Get current task status."""
        return await self.queue.get_status(self.task_id)

    async def cancel(self) -> bool:
        """Cancel the task if pending."""
        return await self.queue.cancel(self.task_id)


class TaskError[TTask](Exception):
    """Task execution error with context.

    **Requirement: R3.4 - Typed TaskError[TTask]**
    """

    def __init__(
        self,
        message: str,
        task: TTask,
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.task = task
        self.original_error = original_error


class RabbitMQTaskQueue[TTask: BaseModel, TResult]:
    """RabbitMQ-backed task queue with typed tasks.

    **Requirement: R3.1 - Generic_TaskQueue[TTask, TResult]**

    Type Parameters:
        TTask: Task payload type (Pydantic BaseModel).
        TResult: Expected result type.

    Example:
        ```python
        class EmailTask(BaseModel):
            to: str
            subject: str
            body: str


        queue = RabbitMQTaskQueue[EmailTask, bool](
            config=RabbitMQConfig(),
            task_type=EmailTask,
        )

        handle = await queue.enqueue(
            EmailTask(
                to="user@example.com",
                subject="Hello",
                body="World",
            )
        )

        result = await handle.result()
        ```
    """

    def __init__(
        self,
        config: RabbitMQConfig,
        task_type: type[TTask],
        result_type: type[TResult] | None = None,
    ) -> None:
        """Initialize task queue.

        Args:
            config: RabbitMQ configuration.
            task_type: Task payload type for deserialization.
            result_type: Optional result type for validation.
        """
        self._config = config
        self._task_type = task_type
        self._result_type = result_type
        self._connection: Any | None = None
        self._channel: Any | None = None
        self._results: dict[str, TaskResult[TResult]] = {}
        self._status: dict[str, TaskStatus] = {}
        self._fallback_queue: asyncio.Queue[tuple[str, TTask]] | None = None

    async def connect(self) -> None:
        """Connect to RabbitMQ."""
        try:
            import aio_pika

            self._connection = await aio_pika.connect_robust(
                self._config.url,
                timeout=self._config.connection_timeout.total_seconds(),
            )
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=self._config.prefetch_count)

            await self._channel.declare_queue(self._config.queue_name, durable=True)
            logger.info(f"Connected to RabbitMQ: {self._config.host}")

        except ImportError:
            logger.warning("aio_pika not installed, using in-memory fallback")
            self._fallback_queue = asyncio.Queue()

    async def close(self) -> None:
        """Close RabbitMQ connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._channel = None

    async def enqueue(
        self,
        task: TTask,
        priority: int = 0,
        delay: timedelta | None = None,
    ) -> TaskHandle[TTask, TResult]:
        """Enqueue a task.

        **Requirement: R3.2 - enqueue() returns TaskHandle[TTask, TResult]**
        **Requirement: R3.8 - Priority queue support**
        """
        task_id = str(uuid4())
        self._status[task_id] = TaskStatus.PENDING

        if self._channel:
            await self._enqueue_rabbitmq(task_id, task, priority, delay)
        elif self._fallback_queue:
            await self._fallback_queue.put((task_id, task))

        return TaskHandle(task_id=task_id, task=task, queue=self)

    async def _enqueue_rabbitmq(
        self,
        task_id: str,
        task: TTask,
        priority: int,
        delay: timedelta | None,
    ) -> None:
        """Enqueue to RabbitMQ."""
        import aio_pika

        message_body = json.dumps({
            "task_id": task_id,
            "payload": task.model_dump(mode="json"),
            "priority": priority,
            "enqueued_at": datetime.now(UTC).isoformat(),
        }).encode()

        message = aio_pika.Message(
            body=message_body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            priority=priority,
            message_id=task_id,
        )

        if delay:
            message.expiration = int(delay.total_seconds() * 1000)

        await self._channel.default_exchange.publish(
            message,
            routing_key=self._config.queue_name,
        )

    async def schedule(
        self,
        task: TTask,
        delay: timedelta,
        priority: int = 0,
    ) -> TaskHandle[TTask, TResult]:
        """Schedule a delayed task.

        **Requirement: R3.7 - Delayed execution**
        """
        return await self.enqueue(task, priority=priority, delay=delay)

    async def get_result(
        self,
        task_id: str,
        timeout: timedelta | None = None,
    ) -> TResult:
        """Get task result."""
        timeout_seconds = timeout.total_seconds() if timeout else 300

        start = asyncio.get_event_loop().time()
        while True:
            if task_id in self._results:
                result = self._results[task_id]
                if result.error:
                    raise TaskError(result.error, None)
                return result.value

            elapsed = asyncio.get_event_loop().time() - start
            if elapsed >= timeout_seconds:
                raise TimeoutError(f"Task {task_id} timed out")

            await asyncio.sleep(0.1)

    async def get_status(self, task_id: str) -> TaskStatus:
        """Get task status."""
        return self._status.get(task_id, TaskStatus.PENDING)

    async def cancel(self, task_id: str) -> bool:
        """Cancel pending task."""
        if self._status.get(task_id) == TaskStatus.PENDING:
            self._status[task_id] = TaskStatus.CANCELLED
            return True
        return False

    def set_result(self, task_id: str, result: TResult) -> None:
        """Set task result (called by worker)."""
        self._results[task_id] = TaskResult(success=True, value=result)
        self._status[task_id] = TaskStatus.COMPLETED

    def set_error(self, task_id: str, error: str) -> None:
        """Set task error (called by worker)."""
        self._results[task_id] = TaskResult(success=False, error=error)
        self._status[task_id] = TaskStatus.FAILED
