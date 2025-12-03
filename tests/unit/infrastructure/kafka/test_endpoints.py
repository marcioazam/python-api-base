"""Unit tests for Kafka infrastructure endpoints.

**Feature: kafka-workflow-integration**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4**
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, UTC


class TestKafkaPublishEndpoint:
    """Tests for POST /kafka/publish endpoint."""

    @pytest.mark.asyncio
    async def test_publish_returns_metadata(self) -> None:
        """Publish endpoint returns message metadata on success.

        **Validates: Requirements 2.1, 2.4**
        """
        from interface.v1.infrastructure_router import kafka_publish, KafkaPublishRequest
        from infrastructure.kafka.message import MessageMetadata

        # Mock producer
        mock_producer = AsyncMock()
        mock_producer.send.return_value = MessageMetadata(
            topic="test-events",
            partition=0,
            offset=42,
            timestamp=datetime.now(UTC),
            key="test-key",
        )

        request = KafkaPublishRequest(
            topic="test-events",
            key="test-key",
            payload={"event": "test", "data": "hello"},
        )

        response = await kafka_publish(request, mock_producer)

        assert response.topic == "test-events"
        assert response.partition == 0
        assert response.offset == 42
        mock_producer.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_with_headers(self) -> None:
        """Publish endpoint passes headers to producer.

        **Validates: Requirements 2.1**
        """
        from interface.v1.infrastructure_router import kafka_publish, KafkaPublishRequest
        from infrastructure.kafka.message import MessageMetadata

        mock_producer = AsyncMock()
        mock_producer.send.return_value = MessageMetadata(
            topic="test-events",
            partition=0,
            offset=1,
            timestamp=datetime.now(UTC),
        )

        request = KafkaPublishRequest(
            topic="test-events",
            payload={"data": "test"},
            headers={"correlation-id": "abc-123"},
        )

        await kafka_publish(request, mock_producer)

        call_kwargs = mock_producer.send.call_args.kwargs
        assert call_kwargs["headers"] == {"correlation-id": "abc-123"}


class TestKafkaStatusEndpoint:
    """Tests for GET /kafka/status endpoint."""

    @pytest.mark.asyncio
    async def test_status_when_kafka_enabled(self) -> None:
        """Status endpoint returns connected=True when producer started.

        **Validates: Requirements 2.2**
        """
        from interface.v1.infrastructure_router import kafka_status

        # Mock request with app state
        mock_request = MagicMock()
        mock_producer = MagicMock()
        mock_producer._started = True
        mock_request.app.state.kafka_producer = mock_producer
        mock_request.app.state.settings.observability.kafka_enabled = True
        mock_request.app.state.settings.observability.kafka_client_id = "test-client"
        mock_request.app.state.settings.observability.kafka_bootstrap_servers = [
            "localhost:9092"
        ]

        response = await kafka_status(mock_request)

        assert response.enabled is True
        assert response.connected is True
        assert response.client_id == "test-client"
        assert response.bootstrap_servers == ["localhost:9092"]

    @pytest.mark.asyncio
    async def test_status_when_kafka_disabled(self) -> None:
        """Status endpoint returns enabled=False when Kafka disabled.

        **Validates: Requirements 2.2**
        """
        from interface.v1.infrastructure_router import kafka_status

        mock_request = MagicMock()
        mock_request.app.state.kafka_producer = None
        mock_request.app.state.settings.observability.kafka_enabled = False

        response = await kafka_status(mock_request)

        assert response.enabled is False
        assert response.connected is False
        assert response.client_id is None
        assert response.bootstrap_servers is None


class TestGetKafkaDependency:
    """Tests for get_kafka dependency."""

    def test_raises_503_when_kafka_not_configured(self) -> None:
        """get_kafka raises HTTPException 503 when producer is None.

        **Validates: Requirements 2.3**
        """
        from interface.v1.infrastructure_router import get_kafka
        from fastapi import HTTPException

        mock_request = MagicMock()
        mock_request.app.state.kafka_producer = None

        with pytest.raises(HTTPException) as exc_info:
            get_kafka(mock_request)

        assert exc_info.value.status_code == 503
        assert "Kafka not configured" in exc_info.value.detail

    def test_returns_producer_when_configured(self) -> None:
        """get_kafka returns producer when available.

        **Validates: Requirements 2.3**
        """
        from interface.v1.infrastructure_router import get_kafka

        mock_request = MagicMock()
        mock_producer = MagicMock()
        mock_request.app.state.kafka_producer = mock_producer

        result = get_kafka(mock_request)

        assert result is mock_producer
