"""RabbitMQ worker implementation.

**Feature: enterprise-generics-2025**
**Requirement: R3.3 - Generic_Worker[TTask, TResult].process()**
**Refactored: 2025 - Extracted from rabbitmq.py for SRP compliance**
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from pydantic import BaseModel

from infrastructure.tasks.retry import ExponentialBackoff, RetryPolicy
from infrastructure.tasks.task import TaskStatus

if TYPE_CHECKING:
    from infrastructure.tasks.rabbitmq.queue import RabbitMQTaskQueue

logger = logging.getLogger(__name__)


class RabbitMQWorker[TTask: BaseModel, TResult]:
    """RabbitMQ task worker.

    **Requirement: R3.3 - Generic_Worker[TTask, TResult].process()**

    Type Parameters:
        TTask: Task payload type.
        TResult: Result type.
    """

    def __init__(
        self,
        queue: RabbitMQTaskQueue[TTask, TResult],
        handler: Callable[[TTask], Awaitable[TResult]],
        retry_policy: RetryPolicy | None = None,
        max_retries: int = 3,
    ) -> None:
        """Initialize worker.

        Args:
            queue: Task queue to consume from.
            handler: Async handler function.
            retry_policy: Optional retry policy.
            max_retries: Maximum retry attempts.
        """
        self._queue = queue
        self._handler = handler
        self._retry_policy = retry_policy or ExponentialBackoff()
        self._running = False
        self._max_retries = max_retries

    async def start(self) -> None:
        """Start consuming tasks."""
        self._running = True

        if self._queue._channel:
            await self._consume_rabbitmq()
        else:
            await self._consume_fallback()

    async def stop(self) -> None:
        """Stop consuming tasks."""
        self._running = False

    async def _consume_rabbitmq(self) -> None:
        """Consume from RabbitMQ."""

        queue = await self._queue._channel.declare_queue(
            self._queue._config.queue_name,
            durable=True,
        )

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                if not self._running:
                    break

                async with message.process():
                    await self._process_message(message.body)

    async def _consume_fallback(self) -> None:
        """Consume from in-memory fallback queue."""
        while self._running:
            try:
                task_id, task = await asyncio.wait_for(
                    self._queue._fallback_queue.get(),
                    timeout=1.0,
                )
                await self._process_task(task_id, task)
            except TimeoutError:
                continue

    async def _process_message(self, body: bytes) -> None:
        """Process RabbitMQ message."""
        data = json.loads(body)
        task_id = data["task_id"]
        payload = self._queue._task_type.model_validate(data["payload"])
        await self._process_task(task_id, payload)

    async def _process_task(self, task_id: str, task: TTask) -> None:
        """Process a task with retry."""
        self._queue._status[task_id] = TaskStatus.RUNNING

        for attempt in range(self._max_retries + 1):
            try:
                result = await self._handler(task)
                self._queue.set_result(task_id, result)
                return
            except Exception as e:
                logger.warning(f"Task {task_id} failed (attempt {attempt + 1}): {e}")
                if self._retry_policy.should_retry(attempt + 1, self._max_retries):
                    delay = self._retry_policy.get_delay(attempt + 1)
                    await asyncio.sleep(delay)
                else:
                    self._queue.set_error(task_id, str(e))
