"""Saga status enumerations.

**Feature: code-review-refactoring, Task 3.2: Extract enums module**
**Validates: Requirements 3.1**
"""

from enum import Enum


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
