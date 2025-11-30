"""Saga orchestrator and execution logic.

**Feature: code-review-refactoring, Task 3.5: Extract orchestrator module**
**Validates: Requirements 3.3**
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
from uuid import uuid4

from .context import SagaContext
from .enums import SagaStatus, StepStatus
from .steps import SagaStep, StepResult


@dataclass
class SagaResult:
    """Result of executing a saga."""

    saga_id: str
    saga_name: str
    status: SagaStatus
    context: SagaContext
    step_results: list[StepResult] = field(default_factory=list)
    error: Exception | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    completed_at: datetime | None = None

    @property
    def is_success(self) -> bool:
        """Check if saga completed successfully."""
        return self.status == SagaStatus.COMPLETED

    @property
    def is_compensated(self) -> bool:
        """Check if saga was compensated (rolled back)."""
        return self.status == SagaStatus.COMPENSATED

    @property
    def duration_ms(self) -> float:
        """Get total saga duration in milliseconds."""
        if self.completed_at is None:
            return 0.0
        delta = self.completed_at - self.started_at
        return delta.total_seconds() * 1000


class Saga[StepT, CompensationT]:
    """Orchestration-based saga for distributed transactions.

    Executes a sequence of steps, and if any step fails,
    automatically compensates (rolls back) completed steps
    in reverse order.
    """

    def __init__(
        self,
        name: str,
        steps: Sequence[SagaStep],
        on_complete: Callable[[SagaResult], Awaitable[None]] | None = None,
        on_compensate: Callable[[SagaResult], Awaitable[None]] | None = None,
        on_failure: Callable[[SagaResult], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize saga."""
        self._name = name
        self._steps = list(steps)
        self._on_complete = on_complete
        self._on_compensate = on_compensate
        self._on_failure = on_failure

    @property
    def name(self) -> str:
        """Get saga name."""
        return self._name

    @property
    def steps(self) -> list[SagaStep]:
        """Get saga steps."""
        return self._steps.copy()

    async def execute(
        self,
        data: dict[str, Any] | None = None,
        saga_id: str | None = None,
    ) -> SagaResult:
        """Execute the saga."""
        saga_id = saga_id or str(uuid4())
        context = SagaContext(saga_id=saga_id, data=data or {})

        result = SagaResult(
            saga_id=saga_id,
            saga_name=self._name,
            status=SagaStatus.RUNNING,
            context=context,
        )

        for step in self._steps:
            step.reset()

        completed_steps: list[SagaStep] = []

        try:
            for step in self._steps:
                step_result = await self._execute_step(step, context)
                result.step_results.append(step_result)

                if step_result.status == StepStatus.COMPLETED:
                    completed_steps.append(step)
                else:
                    result.status = SagaStatus.COMPENSATING
                    result.error = step_result.error
                    await self._compensate(completed_steps, context, result)
                    break
            else:
                result.status = SagaStatus.COMPLETED
                result.completed_at = datetime.now(tz=UTC)

                if self._on_complete:
                    await self._on_complete(result)

        except Exception as e:
            result.status = SagaStatus.FAILED
            result.error = e
            result.completed_at = datetime.now(tz=UTC)

            if self._on_failure:
                await self._on_failure(result)

        return result

    async def _execute_step(self, step: SagaStep, context: SagaContext) -> StepResult:
        """Execute a single saga step."""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now(tz=UTC)

        try:
            await step.action(context)
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now(tz=UTC)

            duration = (step.completed_at - step.started_at).total_seconds() * 1000

            return StepResult(
                step_name=step.name,
                status=StepStatus.COMPLETED,
                duration_ms=duration,
            )

        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = e
            step.completed_at = datetime.now(tz=UTC)

            duration = (step.completed_at - step.started_at).total_seconds() * 1000

            return StepResult(
                step_name=step.name,
                status=StepStatus.FAILED,
                error=e,
                duration_ms=duration,
            )

    async def _compensate(
        self,
        completed_steps: list[SagaStep],
        context: SagaContext,
        result: SagaResult,
    ) -> None:
        """Compensate completed steps in reverse order."""
        compensation_failed = False

        for step in reversed(completed_steps):
            if step.compensation is None:
                step.status = StepStatus.SKIPPED
                continue

            step.status = StepStatus.COMPENSATING

            try:
                await step.compensation(context)
                step.status = StepStatus.COMPENSATED

                result.step_results.append(
                    StepResult(
                        step_name=f"{step.name}_compensation",
                        status=StepStatus.COMPENSATED,
                    )
                )

            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = e
                compensation_failed = True

                result.step_results.append(
                    StepResult(
                        step_name=f"{step.name}_compensation",
                        status=StepStatus.FAILED,
                        error=e,
                    )
                )

        result.completed_at = datetime.now(tz=UTC)

        if compensation_failed:
            result.status = SagaStatus.FAILED
            if self._on_failure:
                await self._on_failure(result)
        else:
            result.status = SagaStatus.COMPENSATED
            if self._on_compensate:
                await self._on_compensate(result)
