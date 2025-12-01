"""Saga context for sharing data between steps.

**Feature: code-review-refactoring, Task 3.3: Extract context module**
**Validates: Requirements 3.2**
"""

from dataclasses import dataclass, field
from typing import Any


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
