"""AsyncAPI builder.

**Feature: code-review-refactoring, Task 18.4: Refactor asyncapi.py**
**Validates: Requirements 5.10**
"""

from .document import AsyncAPIDocument
from .enums import ProtocolType
from .models import (
    ChannelObject,
    InfoObject,
    MessageObject,
    OperationObject,
    SchemaObject,
    ServerObject,
)


class AsyncAPIBuilder:
    """Builder for creating AsyncAPI documents."""

    def __init__(self, title: str, version: str):
        self._info = InfoObject(title=title, version=version)
        self._servers: dict[str, ServerObject] = {}
        self._channels: dict[str, ChannelObject] = {}
        self._operations: dict[str, OperationObject] = {}
        self._messages: dict[str, MessageObject] = {}
        self._schemas: dict[str, SchemaObject] = {}

    def with_description(self, description: str) -> "AsyncAPIBuilder":
        """Set the API description."""
        self._info.description = description
        return self

    def with_contact(self, name: str, email: str) -> "AsyncAPIBuilder":
        """Set contact information."""
        self._info.contact_name = name
        self._info.contact_email = email
        return self

    def with_license(self, name: str, url: str | None = None) -> "AsyncAPIBuilder":
        """Set license information."""
        self._info.license_name = name
        self._info.license_url = url
        return self

    def add_kafka_server(
        self,
        name: str,
        host: str,
        description: str | None = None,
    ) -> "AsyncAPIBuilder":
        """Add a Kafka server."""
        self._servers[name] = ServerObject(
            host=host,
            protocol=ProtocolType.KAFKA,
            description=description,
        )
        return self

    def add_amqp_server(
        self,
        name: str,
        host: str,
        description: str | None = None,
    ) -> "AsyncAPIBuilder":
        """Add an AMQP server."""
        self._servers[name] = ServerObject(
            host=host,
            protocol=ProtocolType.AMQP,
            description=description,
        )
        return self

    def add_redis_server(
        self,
        name: str,
        host: str,
        description: str | None = None,
    ) -> "AsyncAPIBuilder":
        """Add a Redis server."""
        self._servers[name] = ServerObject(
            host=host,
            protocol=ProtocolType.REDIS,
            description=description,
        )
        return self

    def add_channel(
        self,
        name: str,
        address: str,
        description: str | None = None,
    ) -> "AsyncAPIBuilder":
        """Add a channel."""
        self._channels[name] = ChannelObject(
            address=address,
            description=description,
        )
        return self

    def add_publish_operation(
        self,
        name: str,
        channel: str,
        message: MessageObject,
        summary: str | None = None,
    ) -> "AsyncAPIBuilder":
        """Add a publish operation."""
        self._messages[message.name] = message
        self._operations[name] = OperationObject(
            action="send",
            channel=channel,
            messages=[message],
            summary=summary,
        )
        return self

    def add_subscribe_operation(
        self,
        name: str,
        channel: str,
        message: MessageObject,
        summary: str | None = None,
    ) -> "AsyncAPIBuilder":
        """Add a subscribe operation."""
        self._messages[message.name] = message
        self._operations[name] = OperationObject(
            action="receive",
            channel=channel,
            messages=[message],
            summary=summary,
        )
        return self

    def build(self) -> AsyncAPIDocument:
        """Build the AsyncAPI document."""
        doc = AsyncAPIDocument(info=self._info)
        doc.servers = self._servers
        doc.channels = self._channels
        doc.operations = self._operations
        doc.messages = self._messages
        doc.schemas = self._schemas
        return doc
