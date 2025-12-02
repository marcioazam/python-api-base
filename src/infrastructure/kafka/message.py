"""Kafka message types.

**Feature: observability-infrastructure**
**Requirement: R3 - Generic Kafka Producer/Consumer**
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


@dataclass
class MessageMetadata:
    """Kafka message metadata.

    Attributes:
        topic: Topic name
        partition: Partition number
        offset: Message offset
        timestamp: Message timestamp
        key: Message key
        headers: Message headers
    """

    topic: str
    partition: int
    offset: int
    timestamp: datetime | None = None
    key: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


class KafkaMessage(BaseModel, Generic[T]):
    """Generic Kafka message wrapper.

    Type-safe message container for Kafka operations.

    **Feature: observability-infrastructure**
    **Requirement: R3.1 - Message Wrapper**

    Example:
        >>> class UserEvent(BaseModel):
        ...     user_id: str
        ...     action: str
        >>> msg = KafkaMessage[UserEvent](
        ...     payload=UserEvent(user_id="123", action="login"),
        ...     key="user-123",
        ... )
    """

    payload: T
    key: str | None = None
    headers: dict[str, str] = {}
    timestamp: datetime = None  # type: ignore

    # Metadata (populated after send/receive)
    _metadata: MessageMetadata | None = None

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, **data: Any) -> None:
        if "timestamp" not in data or data["timestamp"] is None:
            data["timestamp"] = datetime.now(UTC)
        super().__init__(**data)

    @property
    def metadata(self) -> MessageMetadata | None:
        """Get message metadata."""
        return self._metadata

    def with_metadata(self, metadata: MessageMetadata) -> "KafkaMessage[T]":
        """Set metadata and return self.

        Args:
            metadata: Message metadata

        Returns:
            Self with metadata
        """
        self._metadata = metadata
        return self

    def serialize(self) -> bytes:
        """Serialize message payload to bytes.

        Returns:
            JSON-encoded bytes
        """
        if isinstance(self.payload, BaseModel):
            return self.payload.model_dump_json().encode("utf-8")
        return json.dumps(self.payload).encode("utf-8")

    def serialize_key(self) -> bytes | None:
        """Serialize message key to bytes.

        Returns:
            UTF-8 encoded key or None
        """
        if self.key is None:
            return None
        return self.key.encode("utf-8")

    def serialize_headers(self) -> list[tuple[str, bytes]]:
        """Serialize headers for Kafka.

        Returns:
            List of (key, value) tuples
        """
        return [(k, v.encode("utf-8")) for k, v in self.headers.items()]

    @classmethod
    def deserialize(
        cls,
        payload_class: type[T],
        value: bytes,
        key: bytes | None = None,
        headers: list[tuple[str, bytes]] | None = None,
    ) -> "KafkaMessage[T]":
        """Deserialize message from Kafka.

        Args:
            payload_class: Class to deserialize payload into
            value: Raw message value
            key: Raw message key
            headers: Raw message headers

        Returns:
            Deserialized message
        """
        # Deserialize payload
        if issubclass(payload_class, BaseModel):
            payload = payload_class.model_validate_json(value)
        else:
            payload = json.loads(value)

        # Deserialize key
        decoded_key = key.decode("utf-8") if key else None

        # Deserialize headers
        decoded_headers = {}
        if headers:
            for k, v in headers:
                decoded_headers[k] = v.decode("utf-8") if v else ""

        return cls(
            payload=payload,
            key=decoded_key,
            headers=decoded_headers,
        )
