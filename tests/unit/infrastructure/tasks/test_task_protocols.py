"""Tests for task queue protocols.

Tests for TaskHandler, TaskQueue, and TaskScheduler protocols.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import runtime_checkable

from infrastructure.tasks.protocols import TaskHandler, TaskQueue, TaskScheduler
from infrastructure.tasks.task import Task, TaskStatus


class TestTaskHandlerProtocol:
    """Tests for TaskHandler protocol."""

    def test_is_runtime_checkable(self) -> None:
        """TaskHandler should be runtime checkable."""
        assert hasattr(TaskHandler, "__protocol_attrs__")

    def test_protocol_has_handle_method(self) -> None:
        """TaskHandler should define handle method."""
        assert "handle" in dir(TaskHandler)

    def test_implementation_is_instance(self) -> None:
        """Class implementing handle should be instance of protocol."""

        class MyHandler:
            async def handle(self, payload: str) -> int:
                return len(payload)

        handler = MyHandler()
        assert isinstance(handler, TaskHandler)

    def test_non_implementation_is_not_instance(self) -> None:
        """Class not implementing handle should not be instance."""

        class NotAHandler:
            def process(self, data: str) -> int:
                return 0

        obj = NotAHandler()
        assert not isinstance(obj, TaskHandler)


class TestTaskQueueProtocol:
    """Tests for TaskQueue protocol."""

    def test_is_runtime_checkable(self) -> None:
        """TaskQueue should be runtime checkable."""
        assert hasattr(TaskQueue, "__protocol_attrs__")

    def test_protocol_has_enqueue_method(self) -> None:
        """TaskQueue should define enqueue method."""
        assert "enqueue" in dir(TaskQueue)

    def test_protocol_has_dequeue_method(self) -> None:
        """TaskQueue should define dequeue method."""
        assert "dequeue" in dir(TaskQueue)

    def test_protocol_has_get_task_method(self) -> None:
        """TaskQueue should define get_task method."""
        assert "get_task" in dir(TaskQueue)

    def test_protocol_has_update_task_method(self) -> None:
        """TaskQueue should define update_task method."""
        assert "update_task" in dir(TaskQueue)

    def test_protocol_has_get_tasks_by_status_method(self) -> None:
        """TaskQueue should define get_tasks_by_status method."""
        assert "get_tasks_by_status" in dir(TaskQueue)

    def test_protocol_has_cancel_task_method(self) -> None:
        """TaskQueue should define cancel_task method."""
        assert "cancel_task" in dir(TaskQueue)

    def test_protocol_has_retry_task_method(self) -> None:
        """TaskQueue should define retry_task method."""
        assert "retry_task" in dir(TaskQueue)

    def test_implementation_is_instance(self) -> None:
        """Class implementing all methods should be instance."""

        class MyQueue:
            async def enqueue(self, task: Task) -> str:
                return "id"

            async def dequeue(self) -> Task | None:
                return None

            async def get_task(self, task_id: str) -> Task | None:
                return None

            async def update_task(self, task: Task) -> None:
                pass

            async def get_tasks_by_status(
                self, status: TaskStatus, limit: int = 100
            ) -> Sequence[Task]:
                return []

            async def cancel_task(self, task_id: str) -> bool:
                return False

            async def retry_task(self, task_id: str) -> bool:
                return False

        queue = MyQueue()
        assert isinstance(queue, TaskQueue)


class TestTaskSchedulerProtocol:
    """Tests for TaskScheduler protocol."""

    def test_is_runtime_checkable(self) -> None:
        """TaskScheduler should be runtime checkable."""
        assert hasattr(TaskScheduler, "__protocol_attrs__")

    def test_protocol_has_schedule_method(self) -> None:
        """TaskScheduler should define schedule method."""
        assert "schedule" in dir(TaskScheduler)

    def test_protocol_has_schedule_recurring_method(self) -> None:
        """TaskScheduler should define schedule_recurring method."""
        assert "schedule_recurring" in dir(TaskScheduler)

    def test_protocol_has_cancel_schedule_method(self) -> None:
        """TaskScheduler should define cancel_schedule method."""
        assert "cancel_schedule" in dir(TaskScheduler)

    def test_implementation_is_instance(self) -> None:
        """Class implementing all methods should be instance."""

        class MyScheduler:
            async def schedule(self, task: Task, run_at: datetime) -> str:
                return "schedule-id"

            async def schedule_recurring(
                self, task: Task, cron_expression: str
            ) -> str:
                return "recurring-id"

            async def cancel_schedule(self, schedule_id: str) -> bool:
                return True

        scheduler = MyScheduler()
        assert isinstance(scheduler, TaskScheduler)

    def test_partial_implementation_is_not_instance(self) -> None:
        """Class with partial implementation should not be instance."""

        class PartialScheduler:
            async def schedule(self, task: Task, run_at: datetime) -> str:
                return "id"

        scheduler = PartialScheduler()
        assert not isinstance(scheduler, TaskScheduler)
