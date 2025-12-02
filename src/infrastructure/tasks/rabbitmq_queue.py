"""Compatibility alias for infrastructure.tasks.rabbitmq.queue."""
from infrastructure.tasks.rabbitmq.queue import RabbitMQTaskQueue, TaskHandle, TaskError
__all__ = ["RabbitMQTaskQueue", "TaskHandle", "TaskError"]
