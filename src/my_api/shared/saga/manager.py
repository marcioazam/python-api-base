"""Saga manager for orchestrating multiple sagas.

**Feature: code-review-refactoring, Task 3.7: Extract manager module**
**Validates: Requirements 3.1**
"""

from typing import Any

from .enums import SagaStatus
from .orchestrator import Saga, SagaResult


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
