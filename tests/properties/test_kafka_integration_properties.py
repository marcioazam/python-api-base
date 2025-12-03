"""Property-based tests for Kafka workflow integration.

**Feature: kafka-workflow-integration**
**Validates: Requirements 1.1, 1.2, 1.3, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2**
"""

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from pydantic import BaseModel


class TestKafkaMessageRoundTrip:
    """Property tests for Kafka message serialization.

    **Feature: kafka-workflow-integration, Property 4: Message Serialization Round-Trip**
    **Validates: Requirements 4.1, 4.2**
    """

    @given(
        payload_data=st.dictionaries(
            st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"),
            st.text(max_size=20),
            min_size=1,
            max_size=3,
        ),
        key=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz") | st.none(),
        headers=st.dictionaries(
            st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"),
            st.text(max_size=20),
            max_size=3,
        ),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_message_serialization_round_trip(
        self, payload_data: dict, key: str | None, headers: dict
    ) -> None:
        """
        *For any* valid KafkaMessage with payload and headers,
        serializing then deserializing SHALL produce equivalent message.

        **Feature: kafka-workflow-integration, Property 4: Message Serialization Round-Trip**
        **Validates: Requirements 4.1, 4.2**
        """
        from infrastructure.kafka.message import KafkaMessage

        class TestPayload(BaseModel):
            data: dict

        # Create message
        original = KafkaMessage[TestPayload](
            payload=TestPayload(data=payload_data),
            key=key,
            headers=headers,
        )

        # Serialize
        serialized_value = original.serialize()
        serialized_key = original.serialize_key()
        serialized_headers = original.serialize_headers()

        # Deserialize
        deserialized = KafkaMessage.deserialize(
            payload_class=TestPayload,
            value=serialized_value,
            key=serialized_key,
            headers=serialized_headers,
        )

        # Verify round-trip
        assert deserialized.payload.data == payload_data
        assert deserialized.key == key
        assert deserialized.headers == headers

    @given(
        headers=st.dictionaries(
            st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"),
            st.text(max_size=20),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=50)
    def test_headers_preserved_through_serialization(self, headers: dict) -> None:
        """
        *For any* message headers, serialization SHALL preserve all key-value pairs.

        **Feature: kafka-workflow-integration, Property 4: Message Serialization Round-Trip**
        **Validates: Requirements 4.2**
        """
        from infrastructure.kafka.message import KafkaMessage

        class SimplePayload(BaseModel):
            value: str = "test"

        message = KafkaMessage[SimplePayload](
            payload=SimplePayload(),
            headers=headers,
        )

        serialized = message.serialize_headers()
        
        # Verify all headers are present
        assert len(serialized) == len(headers)
        
        # Deserialize and verify
        deserialized_headers = {}
        for k, v in serialized:
            deserialized_headers[k] = v.decode("utf-8")
        
        assert deserialized_headers == headers


class TestEventPublisher:
    """Property tests for event publishing.

    **Feature: kafka-workflow-integration, Property 5, 6, 7**
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
    """

    @pytest.mark.asyncio
    async def test_noop_publisher_silent_skip(self) -> None:
        """
        *For any* event publish attempt when Kafka is disabled,
        the NoOpEventPublisher SHALL complete without error.

        **Feature: kafka-workflow-integration, Property 6: Silent Skip When Kafka Disabled**
        **Validates: Requirements 3.4**
        """
        from infrastructure.kafka.event_publisher import (
            NoOpEventPublisher,
            DomainEvent,
            ItemCreatedEvent,
        )

        publisher = NoOpEventPublisher()
        event = DomainEvent(
            event_type="ItemCreated",
            entity_type="ItemExample",
            entity_id="test-123",
            payload=ItemCreatedEvent(
                id="test-123",
                name="Test Item",
                sku="SKU-001",
                quantity=10,
                created_by="system",
            ),
        )

        # Should not raise
        await publisher.publish(event, "items-events")

    @pytest.mark.asyncio
    async def test_kafka_publisher_with_none_producer_silent_skip(self) -> None:
        """
        *For any* KafkaEventPublisher with None producer,
        publishing SHALL complete without error.

        **Feature: kafka-workflow-integration, Property 6: Silent Skip When Kafka Disabled**
        **Validates: Requirements 3.4**
        """
        from infrastructure.kafka.event_publisher import (
            KafkaEventPublisher,
            DomainEvent,
            ItemDeletedEvent,
        )

        publisher = KafkaEventPublisher(producer=None)
        event = DomainEvent(
            event_type="ItemDeleted",
            entity_type="ItemExample",
            entity_id="test-456",
            payload=ItemDeletedEvent(
                id="test-456",
                deleted_by="admin",
            ),
        )

        # Should not raise
        await publisher.publish(event, "items-events")

    @given(
        entity_id=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789"),
        name=st.text(min_size=1, max_size=50),
        sku=st.text(min_size=1, max_size=20, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
        quantity=st.integers(min_value=0, max_value=10000),
    )
    @settings(max_examples=50)
    def test_domain_event_creation(
        self, entity_id: str, name: str, sku: str, quantity: int
    ) -> None:
        """
        *For any* valid ItemCreatedEvent data,
        creating a DomainEvent SHALL preserve all fields.

        **Feature: kafka-workflow-integration, Property 5: Domain Event Publishing**
        **Validates: Requirements 3.1**
        """
        from infrastructure.kafka.event_publisher import DomainEvent, ItemCreatedEvent

        payload = ItemCreatedEvent(
            id=entity_id,
            name=name,
            sku=sku,
            quantity=quantity,
            created_by="test-user",
        )

        event = DomainEvent(
            event_type="ItemCreated",
            entity_type="ItemExample",
            entity_id=entity_id,
            payload=payload,
        )

        assert event.event_type == "ItemCreated"
        assert event.entity_type == "ItemExample"
        assert event.entity_id == entity_id
        assert event.payload.id == entity_id
        assert event.payload.name == name
        assert event.payload.sku == sku
        assert event.payload.quantity == quantity


class TestCreateEventPublisher:
    """Tests for event publisher factory function."""

    def test_creates_kafka_publisher_when_producer_available(self) -> None:
        """Factory creates KafkaEventPublisher when producer is provided."""
        from infrastructure.kafka.event_publisher import (
            create_event_publisher,
            KafkaEventPublisher,
        )
        from unittest.mock import MagicMock

        mock_producer = MagicMock()
        publisher = create_event_publisher(mock_producer)

        assert isinstance(publisher, KafkaEventPublisher)

    def test_creates_noop_publisher_when_producer_none(self) -> None:
        """Factory creates NoOpEventPublisher when producer is None."""
        from infrastructure.kafka.event_publisher import (
            create_event_publisher,
            NoOpEventPublisher,
        )

        publisher = create_event_publisher(None)

        assert isinstance(publisher, NoOpEventPublisher)


class TestKafkaConfig:
    """Property tests for Kafka configuration."""

    @given(
        bootstrap_servers=st.lists(
            st.text(min_size=5, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz0123456789:.-"),
            min_size=1,
            max_size=3,
        ),
        client_id=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789-"),
    )
    @settings(max_examples=30)
    def test_config_to_producer_config_preserves_servers(
        self, bootstrap_servers: list[str], client_id: str
    ) -> None:
        """
        *For any* KafkaConfig with bootstrap_servers,
        to_producer_config SHALL include joined servers string.

        **Feature: kafka-workflow-integration, Property 1: Kafka Initialization**
        **Validates: Requirements 1.1**
        """
        from infrastructure.kafka.config import KafkaConfig

        config = KafkaConfig(
            bootstrap_servers=bootstrap_servers,
            client_id=client_id,
        )

        producer_config = config.to_producer_config()

        assert producer_config["bootstrap_servers"] == ",".join(bootstrap_servers)
        assert producer_config["client_id"] == client_id
