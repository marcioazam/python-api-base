"""Compatibility alias for infrastructure.tasks.rabbitmq."""
from infrastructure.tasks.rabbitmq import (
    RabbitMQConfig,
    RabbitMQTaskQueue,
    TaskHandle,
    TaskError,
    RabbitMQWorker,
    RabbitMQRpcClient,
)
__all__ = [
    "RabbitMQConfig",
    "RabbitMQTaskQueue",
    "TaskHandle",
    "TaskError",
    "RabbitMQWorker",
    "RabbitMQRpcClient",
]
