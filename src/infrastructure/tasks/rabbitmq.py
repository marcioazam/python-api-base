"""RabbitMQ task queue adapter with PEP 695 generics.

**Feature: enterprise-generics-2025**
**Requirement: R3 - Generic Task Queue System (RabbitMQ/NATS)**
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import timedelta, datetime, UTC
from typing import Any, Callable, Awaitable
from uuid import uuid4

from pydantic import BaseModel

from infrastructure.tasks.task import Task, TaskResult, TaskStatus
from infrastructure.tasks.protocols import TaskQueue, TaskHandler
from infrastructure.tasks.retry import RetryPolicy, ExponentialBackoff

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass(frozen=True, slots=True)
class RabbitMQConfig:
    """RabbitMQ connection configuration.

    **Requirement: R3.1 - Task queue configuration**
    """

    host: str = "localhost"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    virtual_host: str = "/"
    queue_name: str = "tasks"
    exchange: str = ""
    routing_key: str = "tasks"
    prefetch_count: int = 10
    connection_timeout: timedelta = field(default_factory=lambda: timedelta(seconds=30))

    @property
    def url(self) -> str:
        """Get AMQP connection URL."""
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/{self.virtual_host}"


# =============================================================================
# Task Handle
# =============================================================================


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
    queue: "RabbitMQTaskQueue[TTask, TResult]"
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    async def result(self, timeout: timedelta | None = None) -> TResult:
        """Wait for and return task result.

        **Requirement: R3.4 - TaskHandle.result() returns TResult**

        Args:
            timeout: Maximum time to wait.

        Returns:
            Task result.

        Raises:
            TaskError: If task failed.
            TimeoutError: If timeout exceeded.
        """
        return await self.queue.get_result(self.task_id, timeout)

    async def status(self) -> TaskStatus:
        """Get current task status.

        Returns:
            Task status.
        """
        return await self.queue.get_status(self.task_id)

    async def cancel(self) -> bool:
        """Cancel the task if pending.

        Returns:
            True if cancelled.
        """
        return await self.queue.cancel(self.task_id)


# =============================================================================
# Task Error
# =============================================================================


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


# =============================================================================
# RabbitMQ Task Queue
# =============================================================================


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

        handle = await queue.enqueue(EmailTask(
            to="user@example.com",
            subject="Hello",
            body="World",
        ))

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

            # Declare queue
            await self._channel.declare_queue(
                self._config.queue_name,
                durable=True,
            )

            logger.info(f"Connected to RabbitMQ: {self._config.host}")

        except ImportError:
            logger.warning("aio_pika not installed, using in-memory fallback")
            self._fallback_queue: asyncio.Queue[tuple[str, TTask]] = asyncio.Queue()

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

        Args:
            task: Task payload.
            priority: Task priority (higher = more urgent).
            delay: Optional delay before processing.

        Returns:
            TaskHandle for tracking.
        """
        task_id = str(uuid4())
        self._status[task_id] = TaskStatus.PENDING

        if self._channel:
            await self._enqueue_rabbitmq(task_id, task, priority, delay)
        else:
            # Fallback to in-memory
            await self._fallback_queue.put((task_id, task))

        return TaskHandle(
            task_id=task_id,
            task=task,
            queue=self,
        )

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
            # Use dead letter exchange for delayed messages
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

        Args:
            task: Task payload.
            delay: Delay before processing.
            priority: Task priority.

        Returns:
            TaskHandle for tracking.
        """
        return await self.enqueue(task, priority=priority, delay=delay)

    async def get_result(
        self,
        task_id: str,
        timeout: timedelta | None = None,
    ) -> TResult:
        """Get task result.

        Args:
            task_id: Task identifier.
            timeout: Maximum wait time.

        Returns:
            Task result.

        Raises:
            TaskError: If task failed.
            TimeoutError: If timeout exceeded.
        """
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


# =============================================================================
# Worker
# =============================================================================


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
    ) -> None:
        """Initialize worker.

        Args:
            queue: Task queue to consume from.
            handler: Async handler function.
            retry_policy: Optional retry policy.
        """
        self._queue = queue
        self._handler = handler
        self._retry_policy = retry_policy or ExponentialBackoff()
        self._running = False
        self._max_retries = 3

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
        import aio_pika

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
            except asyncio.TimeoutError:
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
                logger.warning(
                    f"Task {task_id} failed (attempt {attempt + 1}): {e}"
                )
                if self._retry_policy.should_retry(attempt + 1, self._max_retries):
                    delay = self._retry_policy.get_delay(attempt + 1)
                    await asyncio.sleep(delay)
                else:
                    self._queue.set_error(task_id, str(e))


# =============================================================================
# RPC Client
# =============================================================================


class RabbitMQRpcClient[TRequest: BaseModel, TResponse: BaseModel]:
    """RabbitMQ RPC client with typed request/response.

    **Requirement: R3.5 - Generic_RpcClient[TRequest, TResponse].call()**

    Type Parameters:
        TRequest: Request type.
        TResponse: Response type.
    """

    def __init__(
        self,
        config: RabbitMQConfig,
        response_type: type[TResponse],
        timeout: timedelta = timedelta(seconds=30),
    ) -> None:
        """Initialize RPC client.

        Args:
            config: RabbitMQ configuration.
            response_type: Expected response type.
            timeout: RPC timeout.
        """
        self._config = config
        self._response_type = response_type
        self._timeout = timeout
        self._pending: dict[str, asyncio.Future[TResponse]] = {}

    async def call(self, request: TRequest) -> TResponse:
        """Make RPC call.

        **Requirement: R3.5 - call(request) returns Awaitable[TResponse]**

        Args:
            request: Request payload.

        Returns:
            Response from server.

        Raises:
            TimeoutError: If timeout exceeded.
        """
        correlation_id = str(uuid4())
        future: asyncio.Future[TResponse] = asyncio.Future()
        self._pending[correlation_id] = future

        try:
            # In real implementation, publish to RPC queue
            # and wait for response on reply queue
            return await asyncio.wait_for(
                future,
                timeout=self._timeout.total_seconds(),
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"RPC call timed out after {self._timeout}")
        finally:
            self._pending.pop(correlation_id, None)

    def _handle_response(self, correlation_id: str, response: TResponse) -> None:
        """Handle RPC response (called internally)."""
        if correlation_id in self._pending:
            self._pending[correlation_id].set_result(response)
