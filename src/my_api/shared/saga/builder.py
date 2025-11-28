"""Saga builder for fluent API construction.

**Feature: code-review-refactoring, Task 3.6: Extract builder module**
**Validates: Requirements 3.4**
"""

from collections.abc import Awaitable, Callable

from .orchestrator import Saga, SagaResult
from .steps import CompensationAction, SagaStep, StepAction


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
