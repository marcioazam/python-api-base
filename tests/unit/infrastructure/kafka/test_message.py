"""Unit tests for Kafka messages.

**Feature: observability-infrastructure**
**Requirement: R3 - Generic Kafka Producer/Consumer**
"""

import pytest
from datetime import datetime, UTC

from pydantic import BaseModel

from infrastructure.kafka.message import KafkaMessage, MessageMetadata


class UserEvent(BaseModel):
    """Sample event for testing."""

    user_id: str
    action: str
    timestamp: datetime | None = None


class TestMessageMetadata:
    """Tests for MessageMetadata."""

    def test_create_metadata(self) -> None:
        """Test creating metadata."""
        metadata = MessageMetadata(
            topic="test-topic",
            partition=0,
            offset=100,
            key="user-123",
        )

        assert metadata.topic == "test-topic"
        assert metadata.partition == 0
        assert metadata.offset == 100
        assert metadata.key == "user-123"

    def test_metadata_with_timestamp(self) -> None:
        """Test metadata with timestamp."""
        now = datetime.now(UTC)
        metadata = MessageMetadata(
            topic="test",
            partition=0,
            offset=0,
            timestamp=now,
        )

        assert metadata.timestamp == now

    def test_metadata_with_headers(self) -> None:
        """Test metadata with headers."""
        metadata = MessageMetadata(
            topic="test",
            partition=0,
            offset=0,
            headers={"correlation-id": "abc-123"},
        )

        assert metadata.headers["correlation-id"] == "abc-123"


class TestKafkaMessage:
    """Tests for KafkaMessage."""

    def test_create_message(self) -> None:
        """Test creating a message."""
        event = UserEvent(user_id="123", action="login")
        message = KafkaMessage[UserEvent](payload=event, key="user-123")

        assert message.payload.user_id == "123"
        assert message.payload.action == "login"
        assert message.key == "user-123"
        assert message.timestamp is not None

    def test_message_with_headers(self) -> None:
        """Test message with headers."""
        event = UserEvent(user_id="123", action="login")
        message = KafkaMessage[UserEvent](
            payload=event,
            headers={"correlation-id": "abc", "source": "api"},
        )

        assert message.headers["correlation-id"] == "abc"
        assert message.headers["source"] == "api"

    def test_serialize_pydantic(self) -> None:
        """Test serializing Pydantic payload."""
        event = UserEvent(user_id="123", action="login")
        message = KafkaMessage[UserEvent](payload=event)

        serialized = message.serialize()

        assert isinstance(serialized, bytes)
        assert b"user_id" in serialized
        assert b"123" in serialized

    def test_serialize_key(self) -> None:
        """Test serializing message key."""
        message = KafkaMessage[UserEvent](
            payload=UserEvent(user_id="1", action="x"),
            key="user-123",
        )

        key_bytes = message.serialize_key()

        assert key_bytes == b"user-123"

    def test_serialize_key_none(self) -> None:
        """Test serializing None key."""
        message = KafkaMessage[UserEvent](
            payload=UserEvent(user_id="1", action="x"),
            key=None,
        )

        assert message.serialize_key() is None

    def test_serialize_headers(self) -> None:
        """Test serializing headers."""
        message = KafkaMessage[UserEvent](
            payload=UserEvent(user_id="1", action="x"),
            headers={"key1": "value1", "key2": "value2"},
        )

        headers = message.serialize_headers()

        assert len(headers) == 2
        assert ("key1", b"value1") in headers
        assert ("key2", b"value2") in headers

    def test_deserialize(self) -> None:
        """Test deserializing message."""
        raw_value = b'{"user_id": "456", "action": "logout"}'
        raw_key = b"user-456"
        raw_headers = [("source", b"test")]

        message = KafkaMessage.deserialize(
            payload_class=UserEvent,
            value=raw_value,
            key=raw_key,
            headers=raw_headers,
        )

        assert message.payload.user_id == "456"
        assert message.payload.action == "logout"
        assert message.key == "user-456"
        assert message.headers["source"] == "test"

    def test_deserialize_without_key(self) -> None:
        """Test deserializing without key."""
        raw_value = b'{"user_id": "789", "action": "update"}'

        message = KafkaMessage.deserialize(
            payload_class=UserEvent,
            value=raw_value,
        )

        assert message.payload.user_id == "789"
        assert message.key is None

    def test_with_metadata(self) -> None:
        """Test setting metadata."""
        message = KafkaMessage[UserEvent](
            payload=UserEvent(user_id="1", action="test"),
        )
        metadata = MessageMetadata(topic="test", partition=0, offset=100)

        result = message.with_metadata(metadata)

        assert result.metadata is not None
        assert result.metadata.offset == 100
        assert result is message  # Returns same instance

    def test_round_trip_serialization(self) -> None:
        """Test serialize then deserialize."""
        original = KafkaMessage[UserEvent](
            payload=UserEvent(user_id="999", action="create"),
            key="user-999",
            headers={"trace": "xyz"},
        )

        # Serialize
        value_bytes = original.serialize()
        key_bytes = original.serialize_key()
        header_bytes = original.serialize_headers()

        # Deserialize
        restored = KafkaMessage.deserialize(
            payload_class=UserEvent,
            value=value_bytes,
            key=key_bytes,
            headers=header_bytes,
        )

        assert restored.payload.user_id == "999"
        assert restored.payload.action == "create"
        assert restored.key == "user-999"
        assert restored.headers["trace"] == "xyz"
