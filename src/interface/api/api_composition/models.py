"""api_composition models."""

from dataclasses import dataclass, field
from datetime import datetime
from .enums import CompositionStatus


@dataclass
class CallResult[T]:
    """Result of a single API call."""

    name: str
    success: bool
    data: T | None = None
    error: str | None = None
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @classmethod
    def ok(cls, name: str, data: T, duration_ms: float = 0.0) -> "CallResult[T]":
        """Create a successful result."""
        return cls(name=name, success=True, data=data, duration_ms=duration_ms)

    @classmethod
    def fail(cls, name: str, error: str, duration_ms: float = 0.0) -> "CallResult[T]":
        """Create a failed result."""
        return cls(name=name, success=False, error=error, duration_ms=duration_ms)

@dataclass
class CompositionResult[T]:
    """Result of a composition operation."""

    status: CompositionStatus
    results: dict[str, CallResult[T]] = field(default_factory=dict)
    total_duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def successful_results(self) -> dict[str, T]:
        """Get only successful results."""
        return {
            name: result.data
            for name, result in self.results.items()
            if result.success and result.data is not None
        }

    @property
    def failed_results(self) -> dict[str, str]:
        """Get only failed results."""
        return {
            name: result.error or "Unknown error"
            for name, result in self.results.items()
            if not result.success
        }

    @property
    def success_count(self) -> int:
        """Count of successful calls."""
        return sum(1 for r in self.results.values() if r.success)

    @property
    def failure_count(self) -> int:
        """Count of failed calls."""
        return sum(1 for r in self.results.values() if not r.success)

    def get(self, name: str) -> T | None:
        """Get result data by name."""
        result = self.results.get(name)
        return result.data if result and result.success else None
