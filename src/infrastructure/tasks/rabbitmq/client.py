"""RabbitMQ task queue adapter - Re-export module.

**Feature: enterprise-generics-2025**
**Requirement: R3 - Generic Task Queue System (RabbitMQ/NATS)**
**Refactored: 2025 - Split 419 lines into focused modules**

This module re-exports RabbitMQ components from focused modules for backward compatibility.
"""

from infrastructure.tasks.rabbitmq.config import RabbitMQConfig
from infrastructure.tasks.rabbitmq.queue import (
    RabbitMQTaskQueue,
    TaskHandle,
    TaskError,
)
from infrastructure.tasks.rabbitmq.worker import RabbitMQWorker
from infrastructure.tasks.rabbitmq.rpc import RabbitMQRpcClient

__all__ = [
    "RabbitMQConfig",
    "RabbitMQTaskQueue",
    "TaskHandle",
    "TaskError",
    "RabbitMQWorker",
    "RabbitMQRpcClient",
]
