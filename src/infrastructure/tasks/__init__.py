"""Generic Task Queue infrastructure with PEP 695 generics.

Provides type-safe task definitions, queue protocols, and retry policies
for background task processing.

Uses PEP 695 type parameter syntax (Python 3.12+).

Key Generic Types:
    - Task[TPayload, TResult]: Generic task definition
    - TaskQueue[TPayload, TResult]: Queue protocol
    - TaskHandler[TPayload, TResult]: Handler protocol

**Feature: architecture-validation-fixes-2025**
**Validates: Requirements 23.1, 23.2, 23.3, 23.4, 23.5**
"""

from infrastructure.tasks.task import (
    Task,
    TaskPriority,
    TaskStatus,
    TaskResult,
)
from infrastructure.tasks.protocols import (
    TaskHandler,
    TaskQueue,
    TaskScheduler,
)
from infrastructure.tasks.retry import (
    RetryPolicy,
    ExponentialBackoff,
    FixedDelay,
    NoRetry,
)
from infrastructure.tasks.in_memory import InMemoryTaskQueue
from infrastructure.tasks.rabbitmq import (
    RabbitMQConfig,
    RabbitMQRpcClient,
    RabbitMQTaskQueue,
    RabbitMQWorker,
    TaskError,
    TaskHandle,
)

__all__ = [
    # Task
    "Task",
    "TaskPriority",
    "TaskStatus",
    "TaskResult",
    # Protocols
    "TaskHandler",
    "TaskQueue",
    "TaskScheduler",
    # Retry
    "RetryPolicy",
    "ExponentialBackoff",
    "FixedDelay",
    "NoRetry",
    # Implementations
    "InMemoryTaskQueue",
    # RabbitMQ
    "RabbitMQConfig",
    "RabbitMQTaskQueue",
    "RabbitMQWorker",
    "RabbitMQRpcClient",
    "TaskHandle",
    "TaskError",
]
