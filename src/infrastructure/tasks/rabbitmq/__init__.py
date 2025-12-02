"""RabbitMQ task queue implementation.

Provides generic task queue with RabbitMQ backend:
- RabbitMQTaskQueue: Generic queue
- RabbitMQWorker: Task consumer
- RabbitMQRpcClient: RPC pattern

**Feature: enterprise-generics-2025**
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
