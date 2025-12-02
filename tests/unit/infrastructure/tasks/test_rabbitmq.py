"""Unit tests for RabbitMQ task queue.

**Feature: enterprise-generics-2025**
**Requirement: R3 - Generic Task Queue System**
"""

import pytest
import asyncio
from datetime import timedelta

from pydantic import BaseModel

from infrastructure.tasks.rabbitmq import (
    RabbitMQConfig,
    RabbitMQTaskQueue,
    RabbitMQWorker,
    TaskHandle,
    TaskError,
)
from infrastructure.tasks.task import TaskStatus


# =============================================================================
# Test Models
# =============================================================================


class EmailTask(BaseModel):
    """Test email task."""

    to: str
    subject: str
    body: str


class ProcessResult(BaseModel):
    """Test process result."""

    success: bool
    message: str


# =============================================================================
# Tests
# =============================================================================


class TestRabbitMQConfig:
    """Tests for RabbitMQConfig."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = RabbitMQConfig()

        assert config.host == "localhost"
        assert config.port == 5672
        assert config.queue_name == "tasks"

    def test_url_generation(self) -> None:
        """Test AMQP URL generation."""
        config = RabbitMQConfig(
            host="rabbitmq.example.com",
            username="user",
            password="pass",
        )

        assert config.url == "amqp://user:pass@rabbitmq.example.com:5672//"


class TestRabbitMQTaskQueue:
    """Tests for RabbitMQTaskQueue (with fallback)."""

    @pytest.fixture
    def config(self) -> RabbitMQConfig:
        """Create test config."""
        return RabbitMQConfig()

    @pytest.fixture
    def queue(self, config: RabbitMQConfig) -> RabbitMQTaskQueue[EmailTask, bool]:
        """Create test queue (fallback mode)."""
        return RabbitMQTaskQueue[EmailTask, bool](
            config=config,
            task_type=EmailTask,
        )

    @pytest.mark.asyncio
    async def test_enqueue_returns_handle(
        self,
        queue: RabbitMQTaskQueue[EmailTask, bool],
    ) -> None:
        """Test enqueue returns TaskHandle."""
        await queue.connect()  # Will use fallback

        task = EmailTask(
            to="user@example.com",
            subject="Test",
            body="Hello",
        )

        handle = await queue.enqueue(task)

        assert isinstance(handle, TaskHandle)
        assert handle.task == task
        assert handle.task_id is not None

    @pytest.mark.asyncio
    async def test_task_status_pending(
        self,
        queue: RabbitMQTaskQueue[EmailTask, bool],
    ) -> None:
        """Test initial task status is pending."""
        await queue.connect()

        task = EmailTask(to="a@b.com", subject="S", body="B")
        handle = await queue.enqueue(task)

        status = await handle.status()

        assert status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_cancel_pending_task(
        self,
        queue: RabbitMQTaskQueue[EmailTask, bool],
    ) -> None:
        """Test cancelling pending task."""
        await queue.connect()

        task = EmailTask(to="a@b.com", subject="S", body="B")
        handle = await queue.enqueue(task)

        cancelled = await handle.cancel()

        assert cancelled
        assert await handle.status() == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_schedule_delayed_task(
        self,
        queue: RabbitMQTaskQueue[EmailTask, bool],
    ) -> None:
        """Test scheduling delayed task."""
        await queue.connect()

        task = EmailTask(to="a@b.com", subject="S", body="B")
        handle = await queue.schedule(task, delay=timedelta(seconds=60))

        assert handle.task_id is not None

    @pytest.mark.asyncio
    async def test_enqueue_with_priority(
        self,
        queue: RabbitMQTaskQueue[EmailTask, bool],
    ) -> None:
        """Test enqueue with priority."""
        await queue.connect()

        task = EmailTask(to="a@b.com", subject="Urgent", body="Important")
        handle = await queue.enqueue(task, priority=10)

        assert handle.task_id is not None


class TestTaskHandle:
    """Tests for TaskHandle."""

    def test_handle_creation(self) -> None:
        """Test TaskHandle creation."""
        task = EmailTask(to="a@b.com", subject="S", body="B")

        # Create mock queue
        class MockQueue:
            pass

        handle = TaskHandle[EmailTask, bool](
            task_id="test-123",
            task=task,
            queue=MockQueue(),
        )

        assert handle.task_id == "test-123"
        assert handle.task == task


class TestTaskError:
    """Tests for TaskError."""

    def test_error_with_task_context(self) -> None:
        """Test error preserves task context."""
        task = EmailTask(to="a@b.com", subject="S", body="B")
        error = TaskError[EmailTask](
            message="Failed to send",
            task=task,
        )

        assert error.task == task
        assert "Failed to send" in str(error)

    def test_error_with_original_exception(self) -> None:
        """Test error preserves original exception."""
        task = EmailTask(to="a@b.com", subject="S", body="B")
        original = ValueError("Invalid email")
        error = TaskError[EmailTask](
            message="Failed",
            task=task,
            original_error=original,
        )

        assert error.original_error == original


class TestRabbitMQWorker:
    """Tests for RabbitMQWorker."""

    @pytest.mark.asyncio
    async def test_worker_processes_task(self) -> None:
        """Test worker processes task."""
        config = RabbitMQConfig()
        queue = RabbitMQTaskQueue[EmailTask, bool](
            config=config,
            task_type=EmailTask,
        )
        await queue.connect()

        # Track processed tasks
        processed: list[EmailTask] = []

        async def handler(task: EmailTask) -> bool:
            processed.append(task)
            return True

        worker = RabbitMQWorker[EmailTask, bool](
            queue=queue,
            handler=handler,
        )

        # Enqueue task
        task = EmailTask(to="a@b.com", subject="Test", body="Body")
        handle = await queue.enqueue(task)

        # Start worker in background
        worker_task = asyncio.create_task(worker.start())

        # Wait a bit for processing
        await asyncio.sleep(0.2)
        await worker.stop()
        worker_task.cancel()

        try:
            await worker_task
        except asyncio.CancelledError:
            pass

        # Check task was processed
        assert len(processed) == 1
        assert processed[0].to == "a@b.com"

    @pytest.mark.asyncio
    async def test_worker_sets_result(self) -> None:
        """Test worker sets result after processing."""
        config = RabbitMQConfig()
        queue = RabbitMQTaskQueue[EmailTask, str](
            config=config,
            task_type=EmailTask,
        )
        await queue.connect()

        async def handler(task: EmailTask) -> str:
            return "sent"

        worker = RabbitMQWorker[EmailTask, str](
            queue=queue,
            handler=handler,
        )

        task = EmailTask(to="a@b.com", subject="Test", body="Body")
        handle = await queue.enqueue(task)

        # Process in background
        worker_task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.3)
        await worker.stop()
        worker_task.cancel()

        try:
            await worker_task
        except asyncio.CancelledError:
            pass

        # Check status
        status = await handle.status()
        assert status == TaskStatus.COMPLETED


class TestGenericTypeParameters:
    """Tests for generic type parameter behavior."""

    def test_queue_type_parameters(self) -> None:
        """Test queue with different type parameters."""
        config = RabbitMQConfig()

        # Email queue
        email_queue: RabbitMQTaskQueue[EmailTask, bool] = RabbitMQTaskQueue(
            config=config,
            task_type=EmailTask,
        )

        # Process queue
        process_queue: RabbitMQTaskQueue[ProcessResult, str] = RabbitMQTaskQueue(
            config=config,
            task_type=ProcessResult,
        )

        assert email_queue._task_type == EmailTask
        assert process_queue._task_type == ProcessResult

    def test_handle_type_parameters(self) -> None:
        """Test TaskHandle type parameters."""
        task = EmailTask(to="a@b.com", subject="S", body="B")

        class MockQueue:
            pass

        handle: TaskHandle[EmailTask, bool] = TaskHandle(
            task_id="123",
            task=task,
            queue=MockQueue(),
        )

        assert isinstance(handle.task, EmailTask)
