"""Saga Pattern for distributed transactions.

Provides orchestration-based saga implementation for managing
distributed transactions with automatic compensation (rollback).

**Feature: code-review-refactoring, Task 3.8: Create __init__.py with re-exports**
**Validates: Requirements 1.2, 3.5**

Original: saga.py (493 lines)
Refactored: saga/ package (7 files, ~40-180 lines each)

Usage:
    from my_api.shared.saga import Saga, SagaStep, SagaBuilder

    saga = (
        SagaBuilder("create-order")
        .step("create_order", create_order, compensate_order)
        .step("reserve_inventory", reserve_inventory, release_inventory)
        .build()
    )

    result = await saga.execute({"order": order_data})
"""

# Backward compatible re-exports
from .builder import SagaBuilder
from .context import SagaContext
from .enums import SagaStatus, StepStatus
from .manager import SagaOrchestrator
from .orchestrator import Saga, SagaResult
from .steps import CompensationAction, SagaStep, StepAction, StepResult

__all__ = [
    # Context
    "SagaContext",
    # Enums
    "SagaStatus",
    "StepStatus",
    # Steps
    "SagaStep",
    "StepResult",
    "StepAction",
    "CompensationAction",
    # Orchestrator
    "Saga",
    "SagaResult",
    # Builder
    "SagaBuilder",
    # Manager
    "SagaOrchestrator",
]
