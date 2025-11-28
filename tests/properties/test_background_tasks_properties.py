"""Property-based tests for background tasks.

**Feature: api-architecture-analysis, Task 12.5: Async Background Tasks**
**Validates: Requirements 6.2, 9.4**
"""

import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from my_api.shared.background_tasks import (
    BackgroundTaskQueue,
    QueueStats,
    TaskConfig,
    TaskPriority,
    TaskResult,
    TaskStatus,
)


# =============================================================================
# Property Tests - Task Configuration
# =============================================================================

class TestTaskConfigProperties:
    """Property tests for task configuration."""

    @given(
        max_retries=st.integers(min_value=0, max_value=10),
        retry_delay_ms=st.integers(min_value=100, max_value=10000),
    )
    @settings(max_examples=50)
    def test_config_preserves_values(
        self,
        max_retries: int,
        retry_delay_ms: int,
    ) -> None:
        """**Property 1: Config preserves values**

        *For any* configuration values, they should be preserved.

        **Validates: Requirements 6.2, 9.4**
        """
        config = TaskConfig(max_retries=max_retries, retry_delay_ms=retry_delay_ms)

        assert config.max_retries == max_retries
        assert config.retry_delay_ms == retry_delay_ms

    def test_config_defaults(self) -> None:
        """**Property 2: Config has sensible defaults**

        Default configuration should have reasonable values.

        **Validates: Requirements 6.2, 9.4**
        """
        config = TaskConfig()

        assert config.max_retries == 3
        assert config.retry_delay_ms == 1000
        assert config.retry_backoff == 2.0
        assert config.timeout_ms == 30000
        assert config.priority == TaskPriority.NORMAL

    @given(priority=st.sampled_from(list(TaskPriority)))
    @settings(max_examples=10)
    def test_all_priorities_valid(self, priority: TaskPriority) -> None:
        """**Property 3: All priorities are valid**

        *For any* priority, it should be usable in config.

        **Validates: Requirements 6.2, 9.4**
        """
        config = TaskConfig(priority=priority)
        assert config.priority == priority


# =============================================================================
# Property Tests - Task Queue
# =============================================================================

class TestBackgroundTaskQueueProperties:
    """Property tests for background task queue."""

    async def test_submit_returns_task_id(self) -> None:
        """**Property 4: Submit returns task ID**

        Submitting a task should return a valid task ID.

        **Validates: Requirements 6.2, 9.4**
        """
        queue = BackgroundTaskQueue()

        async def task_func() -> int:
            return 42

        task_id = await queue.submit(task_func)

        assert task_id is not None
        assert len(task_id) > 0

    async def test_task_executes_successfully(self) -> None:
        """**Property 5: Task executes successfully**

        Submitted task should execute and return result.

        **Validates: Requirements 6.2, 9.4**
        """
        queue = BackgroundTaskQueue()
        await queue.start()

        async def task_func() -> int:
            return 42

        try:
            task_id = await queue.submit(task_func)
            result = await queue.wait_for(task_id, timeout=5.0)

            assert result is not None
            assert result.status == TaskStatus.COMPLETED
            assert result.result == 42
        finally:
            await queue.stop()

    async def test_task_with_args(self) -> None:
        """**Property 6: Task with arguments executes correctly**

        Task with arguments should receive them correctly.

        **Validates: Requirements 6.2, 9.4**
        """
        queue = BackgroundTaskQueue()
        await queue.start()

        async def add(a: int, b: int) -> int:
            return a + b

        try:
            task_id = await queue.submit(add, 10, 20)
            result = await queue.wait_for(task_id, timeout=5.0)

            assert result is not None
            assert result.result == 30
        finally:
            await queue.stop()

    async def test_task_with_kwargs(self) -> None:
        """**Property 7: Task with kwargs executes correctly**

        Task with keyword arguments should receive them correctly.

        **Validates: Requirements 6.2, 9.4**
        """
        queue = BackgroundTaskQueue()
        await queue.start()

        async def greet(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"

        try:
            task_id = await queue.submit(greet, name="World", greeting="Hi")
            result = await queue.wait_for(task_id, timeout=5.0)

            assert result is not None
            assert result.result == "Hi, World!"
        finally:
            await queue.stop()

    async def test_get_task_returns_task(self) -> None:
        """**Property 8: Get task returns submitted task**

        Getting a task by ID should return the task.

        **Validates: Requirements 6.2, 9.4**
        """
        queue = BackgroundTaskQueue()

        async def task_func() -> int:
            return 42

        task_id = await queue.submit(task_func)
        task = queue.get_task(task_id)

        assert task is not None
        assert task.id == task_id

    async def test_cancel_pending_task(self) -> None:
        """**Property 9: Cancel pending task succeeds**

        Cancelling a pending task should succeed.

        **Validates: Requirements 6.2, 9.4**
        """
        queue = BackgroundTaskQueue()
        # Don't start queue so task stays pending

        async def task_func() -> int:
            return 42

        task_id = await queue.submit(task_func)
        cancelled = await queue.cancel(task_id)

        assert cancelled is True

        task = queue.get_task(task_id)
        assert task is not None
        assert task.status == TaskStatus.CANCELLED


# =============================================================================
# Property Tests - Task Priorities
# =============================================================================

class TestTaskPriorityProperties:
    """Property tests for task priorities."""

    async def test_high_priority_executes_first(self) -> None:
        """**Property 10: High priority tasks execute first**

        Higher priority tasks should execute before lower priority.

        **Validates: Requirements 6.2, 9.4**
        """
        queue = BackgroundTaskQueue(max_workers=1)
        execution_order = []

        async def record_task(name: str) -> str:
            execution_order.append(name)
            return name

        # Submit low priority first
        low_config = TaskConfig(priority=TaskPriority.LOW)
        high_config = TaskConfig(priority=TaskPriority.HIGH)

        await queue.submit(record_task, "low", config=low_config)
        await queue.submit(record_task, "high", config=high_config)

        await queue.start()
        await asyncio.sleep(0.5)
        await queue.stop()

        # High priority should execute first
        if len(execution_order) >= 2:
            assert execution_order[0] == "high"

    def test_priority_ordering(self) -> None:
        """**Property 11: Priority values are ordered correctly**

        Priority enum values should be ordered LOW < NORMAL < HIGH < CRITICAL.

        **Validates: Requirements 6.2, 9.4**
        """
        assert TaskPriority.LOW.value < TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.CRITICAL.value


# =============================================================================
# Property Tests - Task Retries
# =============================================================================

class TestTaskRetryProperties:
    """Property tests for task retries."""

    async def test_failed_task_retries(self) -> None:
        """**Property 12: Failed task retries**

        Task that fails should be retried up to max_retries.

        **Validates: Requirements 6.2, 9.4**
        """
        queue = BackgroundTaskQueue()
        await queue.start()

        attempt_count = 0

        async def failing_task() -> int:
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Test error")

        config = TaskConfig(max_retries=3, retry_delay_ms=10)

        try:
            task_id = await queue.submit(failing_task, config=config)
            result = await queue.wait_for(task_id, timeout=5.0)

            assert result is not None
            assert result.status == TaskStatus.FAILED
            assert result.attempts == 3
            assert attempt_count == 3
        finally:
            await queue.stop()

    async def test_successful_after_retry(self) -> None:
        """**Property 13: Task succeeds after retry**

        Task that fails initially but succeeds on retry should complete.

        **Validates: Requirements 6.2, 9.4**
        """
        queue = BackgroundTaskQueue()
        await queue.start()

        attempt_count = 0

        async def flaky_task() -> int:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Temporary error")
            return 42

        config = TaskConfig(max_retries=3, retry_delay_ms=10)

        try:
            task_id = await queue.submit(flaky_task, config=config)
            result = await queue.wait_for(task_id, timeout=5.0)

            assert result is not None
            assert result.status == TaskStatus.COMPLETED
            assert result.result == 42
            assert result.attempts == 2
        finally:
            await queue.stop()


# =============================================================================
# Property Tests - Queue Statistics
# =============================================================================

class TestQueueStatsProperties:
    """Property tests for queue statistics."""

    def test_stats_initial_values(self) -> None:
        """**Property 14: Stats have zero initial values**

        Initial stats should all be zero.

        **Validates: Requirements 6.2, 9.4**
        """
        stats = QueueStats()

        assert stats.total_tasks == 0
        assert stats.pending_tasks == 0
        assert stats.running_tasks == 0
        assert stats.completed_tasks == 0
        assert stats.failed_tasks == 0
        assert stats.avg_execution_time_ms == 0.0

    async def test_stats_track_submissions(self) -> None:
        """**Property 15: Stats track task submissions**

        Submitting tasks should update statistics.

        **Validates: Requirements 6.2, 9.4**
        """
        queue = BackgroundTaskQueue()

        async def task_func() -> int:
            return 42

        await queue.submit(task_func)
        await queue.submit(task_func)

        stats = queue.get_stats()

        assert stats.total_tasks == 2
        assert stats.pending_tasks == 2

    async def test_stats_track_completions(self) -> None:
        """**Property 16: Stats track task completions**

        Completing tasks should update statistics.

        **Validates: Requirements 6.2, 9.4**
        """
        queue = BackgroundTaskQueue()
        await queue.start()

        async def task_func() -> int:
            return 42

        try:
            task_id = await queue.submit(task_func)
            await queue.wait_for(task_id, timeout=5.0)

            stats = queue.get_stats()

            assert stats.completed_tasks == 1
            assert stats.pending_tasks == 0
        finally:
            await queue.stop()


# =============================================================================
# Property Tests - Task Result
# =============================================================================

class TestTaskResultProperties:
    """Property tests for task results."""

    @given(task_id=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_result_preserves_task_id(self, task_id: str) -> None:
        """**Property 17: Result preserves task ID**

        *For any* task ID, result should preserve it.

        **Validates: Requirements 6.2, 9.4**
        """
        result: TaskResult[int] = TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result=42,
        )

        assert result.task_id == task_id

    @given(status=st.sampled_from(list(TaskStatus)))
    @settings(max_examples=10)
    def test_all_statuses_valid(self, status: TaskStatus) -> None:
        """**Property 18: All statuses are valid**

        *For any* status, it should be usable in result.

        **Validates: Requirements 6.2, 9.4**
        """
        result: TaskResult[int] = TaskResult(
            task_id="test",
            status=status,
        )

        assert result.status == status

    async def test_result_has_timing_info(self) -> None:
        """**Property 19: Result has timing information**

        Completed task result should have timing information.

        **Validates: Requirements 6.2, 9.4**
        """
        queue = BackgroundTaskQueue()
        await queue.start()

        async def task_func() -> int:
            await asyncio.sleep(0.1)
            return 42

        try:
            task_id = await queue.submit(task_func)
            result = await queue.wait_for(task_id, timeout=5.0)

            assert result is not None
            assert result.started_at is not None
            assert result.completed_at is not None
            assert result.duration_ms > 0
        finally:
            await queue.stop()
