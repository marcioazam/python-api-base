"""Fuzzing models.

**Feature: code-review-refactoring, Task 16.3: Refactor fuzzing.py**
**Validates: Requirements 5.3**
"""

import base64
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from .enums import CrashType


@dataclass(frozen=True, slots=True)
class FuzzInput:
    """Represents a fuzz test input."""

    data: bytes
    source: str = "generated"
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def hash(self) -> str:
        """Get SHA256 hash of input data."""
        return hashlib.sha256(self.data).hexdigest()

    @property
    def size(self) -> int:
        """Get size of input in bytes."""
        return len(self.data)

    def to_base64(self) -> str:
        """Encode data as base64."""
        return base64.b64encode(self.data).decode("utf-8")

    @classmethod
    def from_base64(cls, encoded: str, source: str = "decoded") -> "FuzzInput":
        """Create from base64 encoded string."""
        data = base64.b64decode(encoded)
        return cls(data=data, source=source)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "data_b64": self.to_base64(),
            "hash": self.hash,
            "size": self.size,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CrashInfo:
    """Information about a crash found during fuzzing."""

    input_data: FuzzInput
    crash_type: CrashType
    message: str
    stack_trace: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    minimized: bool = False

    @property
    def crash_id(self) -> str:
        """Generate unique crash ID."""
        content = f"{self.crash_type.value}:{self.message}:{self.input_data.hash}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "crash_id": self.crash_id,
            "input": self.input_data.to_dict(),
            "crash_type": self.crash_type.value,
            "message": self.message,
            "stack_trace": self.stack_trace,
            "timestamp": self.timestamp.isoformat(),
            "minimized": self.minimized,
        }


@dataclass
class CoverageInfo:
    """Code coverage information from fuzzing."""

    lines_covered: int = 0
    lines_total: int = 0
    branches_covered: int = 0
    branches_total: int = 0
    functions_covered: int = 0
    functions_total: int = 0

    @property
    def line_coverage(self) -> float:
        """Get line coverage percentage."""
        if self.lines_total == 0:
            return 0.0
        return (self.lines_covered / self.lines_total) * 100

    @property
    def branch_coverage(self) -> float:
        """Get branch coverage percentage."""
        if self.branches_total == 0:
            return 0.0
        return (self.branches_covered / self.branches_total) * 100

    def merge(self, other: "CoverageInfo") -> "CoverageInfo":
        """Merge with another coverage info."""
        return CoverageInfo(
            lines_covered=max(self.lines_covered, other.lines_covered),
            lines_total=max(self.lines_total, other.lines_total),
            branches_covered=max(self.branches_covered, other.branches_covered),
            branches_total=max(self.branches_total, other.branches_total),
            functions_covered=max(self.functions_covered, other.functions_covered),
            functions_total=max(self.functions_total, other.functions_total),
        )


@dataclass
class FuzzingStats:
    """Statistics from a fuzzing run."""

    total_inputs: int = 0
    unique_inputs: int = 0
    crashes_found: int = 0
    timeouts: int = 0
    executions_per_second: float = 0.0
    coverage: CoverageInfo = field(default_factory=CoverageInfo)
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        end = self.end_time or datetime.now(UTC)
        return (end - self.start_time).total_seconds()

    def record_input(self, is_unique: bool = False) -> None:
        """Record an input execution."""
        self.total_inputs += 1
        if is_unique:
            self.unique_inputs += 1

    def record_crash(self) -> None:
        """Record a crash."""
        self.crashes_found += 1

    def record_timeout(self) -> None:
        """Record a timeout."""
        self.timeouts += 1

    def update_exec_speed(self) -> None:
        """Update executions per second."""
        duration = self.duration_seconds
        if duration > 0:
            self.executions_per_second = self.total_inputs / duration
