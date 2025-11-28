"""Saga Pattern for distributed transactions.

Provides orchestration-based saga implementation for managing
distributed transactions with automatic compensation (rollback).

**Feature: api-architecture-analysis, Task 3.5: Saga Pattern**
**Validates: Requirements 9.3**

Usage:
    from my_api.shared.saga import Saga, SagaStep, SagaBuilder

    # Define saga steps
    async def create_order(ctx: SagaContext) -> None:
        order = await order_service.create(ctx.data["order"])
        ctx.set("order_id", order.id)

    async def compensate_order(ctx: SagaContext) -> None:
        await order_service.cancel(ctx.get("order_id"))

    async def reserve_inventory(ctx: SagaContext) -> None:
        await inventory_service.reserve(ctx.get("order_id"))

    async def release_inventory(ctx: SagaContext) -> None:
        await inventory_service.release(ctx.get("order_id"))

    async def charge_payment(ctx: SagaContext) -> None:
        await payment_service.charge(ctx.data["payment"])

    async def refund_payment(ctx: SagaContext) -> None:
        await payment_service.refund(ctx.get("order_id"))

    # Build and execute saga
    saga = (
        SagaBuilder("create-order")
        .step("create_order", create_order, compensate_order)
        .step("reserve_inventory", reserve_inventory, release_inventory)
        .step("charge_payment", charge_payment, refund_payment)
        .build()
    )

    result = await saga.execute({"order": order_data, "payment": payment_data})
    if result.is_success:
        print(f"Order created: {result.context.get('order_id')}")
    else:
        print(f"Saga failed: {result.error}")
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import uuid4

# Type variables
StepT = TypeVar("StepT")
CompensationT = TypeVar("CompensationT")
ResultT = TypeVar("ResultT")


class SagaStatus(str, Enum):
    """Status of a saga execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"


class StepStatus(str, Enum):
    """Status of a saga step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SagaContext:
    """Context passed between saga steps.

    Holds data shared across steps and allows steps to
    communicate results to subsequent steps.
    """

    saga_id: str
    data: dict[str, Any] = field(default_factory=dict)
    _results: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the context.

        Args:
            key: The key to retrieve.
            default: Default value if key not found.

        Returns:
            The value or default.
        """
        return self._results.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the context.

        Args:
            key: The key to set.
            value: The value to store.
        """
        self._results[key] = value

    def has(self, key: str) -> bool:
        """Check if a key exists in the context.

        Args:
            key: The key to check.

        Returns:
            True if the key exists.
        """
        return key in self._results

    def clear_results(self) -> None:
        """Clear all results from the context."""
        self._results.clear()


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


@dataclass
class SagaResult:
    """Result of executing a saga."""

    saga_id: str
    saga_name: str
    status: SagaStatus
    context: SagaContext
    step_results: list[StepResult] = field(default_factory=list)
    error: Exception | None = None
    started_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
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


class Saga(Generic[StepT, CompensationT]):
    """Orchestration-based saga for distributed transactions.

    Executes a sequence of steps, and if any step fails,
    automatically compensates (rolls back) completed steps
    in reverse order.

    Type Parameters:
        StepT: Type of step actions.
        CompensationT: Type of compensation actions.
    """

    def __init__(
        self,
        name: str,
        steps: Sequence[SagaStep],
        on_complete: Callable[[SagaResult], Awaitable[None]] | None = None,
        on_compensate: Callable[[SagaResult], Awaitable[None]] | None = None,
        on_failure: Callable[[SagaResult], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize saga.

        Args:
            name: Saga name for identification.
            steps: Sequence of saga steps.
            on_complete: Callback when saga completes successfully.
            on_compensate: Callback when saga is compensated.
            on_failure: Callback when saga fails (compensation also failed).
        """
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
        """Execute the saga.

        Args:
            data: Initial data for the saga context.
            saga_id: Optional saga ID (generated if not provided).

        Returns:
            SagaResult with execution details.
        """
        saga_id = saga_id or str(uuid4())
        context = SagaContext(saga_id=saga_id, data=data or {})

        result = SagaResult(
            saga_id=saga_id,
            saga_name=self._name,
            status=SagaStatus.RUNNING,
            context=context,
        )

        # Reset all steps
        for step in self._steps:
            step.reset()

        completed_steps: list[SagaStep] = []

        try:
            # Execute steps in order
            for step in self._steps:
                step_result = await self._execute_step(step, context)
                result.step_results.append(step_result)

                if step_result.status == StepStatus.COMPLETED:
                    completed_steps.append(step)
                else:
                    # Step failed, start compensation
                    result.status = SagaStatus.COMPENSATING
                    result.error = step_result.error
                    await self._compensate(completed_steps, context, result)
                    break
            else:
                # All steps completed successfully
                result.status = SagaStatus.COMPLETED
                result.completed_at = datetime.now(tz=timezone.utc)

                if self._on_complete:
                    await self._on_complete(result)

        except Exception as e:
            result.status = SagaStatus.FAILED
            result.error = e
            result.completed_at = datetime.now(tz=timezone.utc)

            if self._on_failure:
                await self._on_failure(result)

        return result

    async def _execute_step(
        self, step: SagaStep, context: SagaContext
    ) -> StepResult:
        """Execute a single saga step.

        Args:
            step: The step to execute.
            context: Saga context.

        Returns:
            StepResult with execution details.
        """
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now(tz=timezone.utc)

        try:
            await step.action(context)
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now(tz=timezone.utc)

            duration = (step.completed_at - step.started_at).total_seconds() * 1000

            return StepResult(
                step_name=step.name,
                status=StepStatus.COMPLETED,
                duration_ms=duration,
            )

        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = e
            step.completed_at = datetime.now(tz=timezone.utc)

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
        """Compensate completed steps in reverse order.

        Args:
            completed_steps: Steps that completed successfully.
            context: Saga context.
            result: Saga result to update.
        """
        compensation_failed = False

        # Compensate in reverse order
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

        result.completed_at = datetime.now(tz=timezone.utc)

        if compensation_failed:
            result.status = SagaStatus.FAILED
            if self._on_failure:
                await self._on_failure(result)
        else:
            result.status = SagaStatus.COMPENSATED
            if self._on_compensate:
                await self._on_compensate(result)


class SagaBuilder:
    """Fluent builder for creating sagas.

    Provides a convenient way to construct sagas with
    a fluent API.
    """

    def __init__(self, name: str) -> None:
        """Initialize builder.

        Args:
            name: Saga name.
        """
        self._name = name
        self._steps: list[SagaStep] = []
        self._on_complete: Callable[[SagaResult], Awaitable[None]] | None = None
        self._on_compensate: Callable[[SagaResult], Awaitable[None]] | None = None
        self._on_failure: Callable[[SagaResult], Awaitable[None]] | None = None

    def step(
        self,
        name: str,
        action: StepAction,
        compensation: CompensationAction | None = None,
    ) -> "SagaBuilder":
        """Add a step to the saga.

        Args:
            name: Step name.
            action: Step action function.
            compensation: Optional compensation function.

        Returns:
            Self for chaining.
        """
        self._steps.append(
            SagaStep(name=name, action=action, compensation=compensation)
        )
        return self

    def on_complete(
        self, callback: Callable[[SagaResult], Awaitable[None]]
    ) -> "SagaBuilder":
        """Set completion callback.

        Args:
            callback: Function to call on successful completion.

        Returns:
            Self for chaining.
        """
        self._on_complete = callback
        return self

    def on_compensate(
        self, callback: Callable[[SagaResult], Awaitable[None]]
    ) -> "SagaBuilder":
        """Set compensation callback.

        Args:
            callback: Function to call after compensation.

        Returns:
            Self for chaining.
        """
        self._on_compensate = callback
        return self

    def on_failure(
        self, callback: Callable[[SagaResult], Awaitable[None]]
    ) -> "SagaBuilder":
        """Set failure callback.

        Args:
            callback: Function to call on failure.

        Returns:
            Self for chaining.
        """
        self._on_failure = callback
        return self

    def build(self) -> Saga[StepAction, CompensationAction]:
        """Build the saga.

        Returns:
            Configured Saga instance.

        Raises:
            ValueError: If no steps were added.
        """
        if not self._steps:
            raise ValueError("Saga must have at least one step")

        return Saga(
            name=self._name,
            steps=self._steps,
            on_complete=self._on_complete,
            on_compensate=self._on_compensate,
            on_failure=self._on_failure,
        )


# =============================================================================
# Saga Orchestrator for Managing Multiple Sagas
# =============================================================================


class SagaOrchestrator:
    """Orchestrator for managing and tracking saga executions.

    Provides saga registration, execution tracking, and
    history management.
    """

    def __init__(self) -> None:
        """Initialize orchestrator."""
        self._sagas: dict[str, Saga[Any, Any]] = {}
        self._history: list[SagaResult] = []
        self._max_history: int = 1000

    def register(self, saga: Saga[Any, Any]) -> None:
        """Register a saga.

        Args:
            saga: Saga to register.
        """
        self._sagas[saga.name] = saga

    def unregister(self, name: str) -> bool:
        """Unregister a saga.

        Args:
            name: Saga name.

        Returns:
            True if saga was unregistered.
        """
        if name in self._sagas:
            del self._sagas[name]
            return True
        return False

    def get_saga(self, name: str) -> Saga[Any, Any] | None:
        """Get a registered saga.

        Args:
            name: Saga name.

        Returns:
            Saga or None if not found.
        """
        return self._sagas.get(name)

    async def execute(
        self,
        saga_name: str,
        data: dict[str, Any] | None = None,
    ) -> SagaResult:
        """Execute a registered saga.

        Args:
            saga_name: Name of the saga to execute.
            data: Initial data for the saga.

        Returns:
            SagaResult with execution details.

        Raises:
            ValueError: If saga is not registered.
        """
        saga = self._sagas.get(saga_name)
        if saga is None:
            raise ValueError(f"Saga '{saga_name}' is not registered")

        result = await saga.execute(data)
        self._add_to_history(result)

        return result

    def _add_to_history(self, result: SagaResult) -> None:
        """Add result to history with size limit."""
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

    def get_history(
        self,
        saga_name: str | None = None,
        status: SagaStatus | None = None,
        limit: int = 100,
    ) -> list[SagaResult]:
        """Get saga execution history.

        Args:
            saga_name: Filter by saga name.
            status: Filter by status.
            limit: Maximum results to return.

        Returns:
            List of saga results.
        """
        results = self._history

        if saga_name:
            results = [r for r in results if r.saga_name == saga_name]

        if status:
            results = [r for r in results if r.status == status]

        return results[-limit:]

    def clear_history(self) -> None:
        """Clear execution history."""
        self._history.clear()

