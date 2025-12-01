"""AsyncAPI model objects.

**Feature: code-review-refactoring, Task 18.4: Refactor asyncapi.py**
**Validates: Requirements 5.10**
"""

from dataclasses import dataclass, field
from typing import Any

from .enums import ProtocolType


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

    action: str
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
