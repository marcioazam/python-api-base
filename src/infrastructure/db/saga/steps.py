"""Saga step definitions and results.

**Feature: code-review-refactoring, Task 3.4: Extract steps module**
**Validates: Requirements 3.1**
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime

from .context import SagaContext
from .enums import StepStatus

# Type aliases for step functions
type StepAction = Callable[[SagaContext], Awaitable[None]]
type CompensationAction = Callable[[SagaContext], Awaitable[None]]


@dataclass
class SagaStep:
    """Represents a single step in a saga.

    Each step has an action to execute and an optional
    compensation action for rollback.
    """

    name: str
    action: StepAction
    compensation: CompensationAction | None = None
    status: StepStatus = StepStatus.PENDING
    error: Exception | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def reset(self) -> None:
        """Reset step to initial state."""
        self.status = StepStatus.PENDING
        self.error = None
        self.started_at = None
        self.completed_at = None


@dataclass
class StepResult:
    """Result of executing a saga step."""

    step_name: str
    status: StepStatus
    error: Exception | None = None
    duration_ms: float = 0.0
