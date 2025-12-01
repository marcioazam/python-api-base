"""AsyncAPI document.

**Feature: code-review-refactoring, Task 18.4: Refactor asyncapi.py**
**Validates: Requirements 5.10**
"""

from dataclasses import dataclass, field
from typing import Any

from .models import (
    ChannelObject,
    InfoObject,
    MessageObject,
    OperationObject,
    SchemaObject,
    ServerObject,
)


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
