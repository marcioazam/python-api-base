"""AsyncAPI helper functions.

**Feature: code-review-refactoring, Task 18.4: Refactor asyncapi.py**
**Validates: Requirements 5.10**
"""

from .models import MessageObject, SchemaObject


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
