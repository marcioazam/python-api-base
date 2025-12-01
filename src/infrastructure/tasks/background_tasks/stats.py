"""Background task queue statistics.

**Feature: full-codebase-review-2025, Task 1.5: Refactor background_tasks**
**Validates: Requirements 9.2**
"""

from pydantic import BaseModel


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
