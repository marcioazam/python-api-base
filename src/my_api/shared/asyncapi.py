"""AsyncAPI support for event-driven architecture documentation.

Implements AsyncAPI 3.0 specification for documenting message-driven APIs.

**Feature: api-architecture-analysis, Property 2: Event schema documentation**
**Validates: Requirements 9.5**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProtocolType(str, Enum):
    """Supported message broker protocols."""

    KAFKA = "kafka"
    AMQP = "amqp"
    MQTT = "mqtt"
    WS = "ws"
    HTTP = "http"
    REDIS = "redis"
    NATS = "nats"


class SecuritySchemeType(str, Enum):
    """Security scheme types."""

    USER_PASSWORD = "userPassword"
    API_KEY = "apiKey"
    X509 = "X509"
    SYMMETRIC_ENCRYPTION = "symmetricEncryption"
    ASYMMETRIC_ENCRYPTION = "asymmetricEncryption"
    HTTP_API_KEY = "httpApiKey"
    HTTP = "http"
    OAUTH2 = "oauth2"
    OPENID_CONNECT = "openIdConnect"
    PLAIN = "plain"
    SCRAM_SHA256 = "scramSha256"
    SCRAM_SHA512 = "scramSha512"
    GSSAPI = "gssapi"


@dataclass(slots=True)
class SchemaObject:
    """JSON Schema object for message payloads."""

    schema_type: str
    properties: dict[str, dict[str, Any]] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)
    description: str | None = None
    example: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"type": self.schema_type}
        if self.properties:
            result["properties"] = self.properties
        if self.required:
            result["required"] = self.required
        if self.description:
            result["description"] = self.description
        if self.example is not None:
            result["example"] = self.example
        return result


@dataclass(slots=True)
class MessageObject:
    """AsyncAPI message object."""

    name: str
    payload: SchemaObject
    content_type: str = "application/json"
    description: str | None = None
    headers: SchemaObject | None = None
    correlation_id: str | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "name": self.name,
            "contentType": self.content_type,
            "payload": self.payload.to_dict(),
        }
        if self.description:
            result["description"] = self.description
        if self.headers:
            result["headers"] = self.headers.to_dict()
        if self.correlation_id:
            result["correlationId"] = {"location": self.correlation_id}
        if self.tags:
            result["tags"] = [{"name": tag} for tag in self.tags]
        return result


@dataclass(slots=True)
class OperationObject:
    """AsyncAPI operation object."""

    action: str  # "send" or "receive"
    channel: str
    messages: list[MessageObject] = field(default_factory=list)
    summary: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "action": self.action,
            "channel": {"$ref": f"#/channels/{self.channel}"},
        }
        if self.messages:
            result["messages"] = [
                {"$ref": f"#/components/messages/{msg.name}"} for msg in self.messages
            ]
        if self.summary:
            result["summary"] = self.summary
        if self.description:
            result["description"] = self.description
        if self.tags:
            result["tags"] = [{"name": tag} for tag in self.tags]
        return result


@dataclass(slots=True)
class ChannelObject:
    """AsyncAPI channel object."""

    address: str
    description: str | None = None
    messages: dict[str, MessageObject] = field(default_factory=dict)
    parameters: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {"address": self.address}
        if self.description:
            result["description"] = self.description
        if self.messages:
            result["messages"] = {
                name: {"$ref": f"#/components/messages/{name}"}
                for name in self.messages
            }
        if self.parameters:
            result["parameters"] = self.parameters
        return result


@dataclass(slots=True)
class ServerObject:
    """AsyncAPI server object."""

    host: str
    protocol: ProtocolType
    protocol_version: str | None = None
    description: str | None = None
    variables: dict[str, dict[str, Any]] = field(default_factory=dict)
    security: list[dict[str, list[str]]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "host": self.host,
            "protocol": self.protocol.value,
        }
        if self.protocol_version:
            result["protocolVersion"] = self.protocol_version
        if self.description:
            result["description"] = self.description
        if self.variables:
            result["variables"] = self.variables
        if self.security:
            result["security"] = self.security
        return result


@dataclass(slots=True)
class InfoObject:
    """AsyncAPI info object."""

    title: str
    version: str
    description: str | None = None
    terms_of_service: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    license_name: str | None = None
    license_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "title": self.title,
            "version": self.version,
        }
        if self.description:
            result["description"] = self.description
        if self.terms_of_service:
            result["termsOfService"] = self.terms_of_service
        if self.contact_name or self.contact_email:
            result["contact"] = {}
            if self.contact_name:
                result["contact"]["name"] = self.contact_name
            if self.contact_email:
                result["contact"]["email"] = self.contact_email
        if self.license_name:
            result["license"] = {"name": self.license_name}
            if self.license_url:
                result["license"]["url"] = self.license_url
        return result


@dataclass(slots=True)
class AsyncAPIDocument:
    """AsyncAPI document builder."""

    info: InfoObject
    servers: dict[str, ServerObject] = field(default_factory=dict)
    channels: dict[str, ChannelObject] = field(default_factory=dict)
    operations: dict[str, OperationObject] = field(default_factory=dict)
    messages: dict[str, MessageObject] = field(default_factory=dict)
    schemas: dict[str, SchemaObject] = field(default_factory=dict)

    def add_server(self, name: str, server: ServerObject) -> "AsyncAPIDocument":
        """Add a server to the document."""
        self.servers[name] = server
        return self

    def add_channel(self, name: str, channel: ChannelObject) -> "AsyncAPIDocument":
        """Add a channel to the document."""
        self.channels[name] = channel
        return self

    def add_operation(
        self, name: str, operation: OperationObject
    ) -> "AsyncAPIDocument":
        """Add an operation to the document."""
        self.operations[name] = operation
        return self

    def add_message(self, message: MessageObject) -> "AsyncAPIDocument":
        """Add a message to the document."""
        self.messages[message.name] = message
        return self

    def add_schema(self, name: str, schema: SchemaObject) -> "AsyncAPIDocument":
        """Add a schema to the document."""
        self.schemas[name] = schema
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert to AsyncAPI document dictionary."""
        result: dict[str, Any] = {
            "asyncapi": "3.0.0",
            "info": self.info.to_dict(),
        }
        if self.servers:
            result["servers"] = {
                name: server.to_dict() for name, server in self.servers.items()
            }
        if self.channels:
            result["channels"] = {
                name: channel.to_dict() for name, channel in self.channels.items()
            }
        if self.operations:
            result["operations"] = {
                name: op.to_dict() for name, op in self.operations.items()
            }
        if self.messages or self.schemas:
            result["components"] = {}
            if self.messages:
                result["components"]["messages"] = {
                    name: msg.to_dict() for name, msg in self.messages.items()
                }
            if self.schemas:
                result["components"]["schemas"] = {
                    name: schema.to_dict() for name, schema in self.schemas.items()
                }
        return result

    def to_yaml(self) -> str:
        """Convert to YAML string."""
        import yaml

        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json

        return json.dumps(self.to_dict(), indent=2)


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


def create_event_schema(
    name: str,
    properties: dict[str, str],
    required: list[str] | None = None,
    description: str | None = None,
) -> SchemaObject:
    """Create a schema object for an event payload."""
    type_mapping = {
        "string": {"type": "string"},
        "int": {"type": "integer"},
        "integer": {"type": "integer"},
        "float": {"type": "number"},
        "number": {"type": "number"},
        "bool": {"type": "boolean"},
        "boolean": {"type": "boolean"},
        "array": {"type": "array"},
        "object": {"type": "object"},
        "datetime": {"type": "string", "format": "date-time"},
        "uuid": {"type": "string", "format": "uuid"},
        "email": {"type": "string", "format": "email"},
        "uri": {"type": "string", "format": "uri"},
    }
    props = {
        prop_name: type_mapping.get(prop_type, {"type": prop_type})
        for prop_name, prop_type in properties.items()
    }
    return SchemaObject(
        schema_type="object",
        properties=props,
        required=required or [],
        description=description,
    )


def create_event_message(
    name: str,
    schema: SchemaObject,
    description: str | None = None,
    correlation_id: str | None = None,
) -> MessageObject:
    """Create a message object for an event."""
    return MessageObject(
        name=name,
        payload=schema,
        description=description,
        correlation_id=correlation_id,
    )
