"""Tests for RabbitMQ client re-export module.

Verifies that all exports from focused modules are available.
"""

from infrastructure.tasks.rabbitmq.client import (
    RabbitMQConfig,
    RabbitMQRpcClient,
    RabbitMQTaskQueue,
    RabbitMQWorker,
    TaskError,
    TaskHandle,
)


class TestRabbitMQClientReExports:
    """Tests for re-exported components."""

    def test_rabbitmq_config_is_class(self) -> None:
        """RabbitMQConfig should be a class."""
        assert isinstance(RabbitMQConfig, type)

    def test_rabbitmq_task_queue_is_class(self) -> None:
        """RabbitMQTaskQueue should be a class."""
        assert isinstance(RabbitMQTaskQueue, type)

    def test_rabbitmq_rpc_client_is_class(self) -> None:
        """RabbitMQRpcClient should be a class."""
        assert isinstance(RabbitMQRpcClient, type)

    def test_rabbitmq_worker_is_class(self) -> None:
        """RabbitMQWorker should be a class."""
        assert isinstance(RabbitMQWorker, type)

    def test_task_error_is_exception(self) -> None:
        """TaskError should be an exception class."""
        assert issubclass(TaskError, Exception)

    def test_task_handle_is_class(self) -> None:
        """TaskHandle should be a class."""
        assert isinstance(TaskHandle, type)

    def test_rabbitmq_config_can_be_instantiated(self) -> None:
        """RabbitMQConfig should be instantiable with defaults."""
        config = RabbitMQConfig()
        assert config is not None

    def test_task_error_can_be_raised(self) -> None:
        """TaskError can be raised and caught."""
        from infrastructure.tasks.task import Task

        task = Task(name="test-task", payload={}, handler="test.handler")
        try:
            raise TaskError("test error", task)
        except TaskError as e:
            assert e.task == task
