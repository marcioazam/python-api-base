"""Property-based tests for AsyncAPI support.

**Feature: api-architecture-analysis, Property 2: Event schema documentation**
**Validates: Requirements 9.5**
"""

import json

from hypothesis import given, settings, strategies as st

from infrastructure.messaging.asyncapi import (
    AsyncAPIBuilder,
    AsyncAPIDocument,
    ChannelObject,
    InfoObject,
    MessageObject,
    OperationObject,
    ProtocolType,
    SchemaObject,
    ServerObject,
    create_event_message,
    create_event_schema,
)


identifier_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"),
    min_size=1,
    max_size=20,
)

version_strategy = st.from_regex(r"[0-9]+\.[0-9]+\.[0-9]+", fullmatch=True)


class TestSchemaObject:
    """Tests for SchemaObject."""

    @given(
        schema_type=st.sampled_from(["object", "string", "integer", "array"]),
        description=st.text(max_size=50) | st.none(),
    )
    @settings(max_examples=50)
    def test_to_dict_contains_type(self, schema_type: str, description: str | None):
        """to_dict should contain the schema type."""
        schema = SchemaObject(schema_type=schema_type, description=description)
        result = schema.to_dict()
        assert result["type"] == schema_type

    @given(prop_name=identifier_strategy)
    @settings(max_examples=50)
    def test_properties_included_in_dict(self, prop_name: str):
        """Properties should be included in to_dict."""
        schema = SchemaObject(
            schema_type="object",
            properties={prop_name: {"type": "string"}},
        )
        result = schema.to_dict()
        assert prop_name in result["properties"]

    @given(field_name=identifier_strategy)
    @settings(max_examples=50)
    def test_required_fields_included(self, field_name: str):
        """Required fields should be included in to_dict."""
        schema = SchemaObject(
            schema_type="object",
            required=[field_name],
        )
        result = schema.to_dict()
        assert field_name in result["required"]


class TestMessageObject:
    """Tests for MessageObject."""

    @given(name=identifier_strategy)
    @settings(max_examples=50)
    def test_to_dict_contains_name(self, name: str):
        """to_dict should contain the message name."""
        payload = SchemaObject(schema_type="object")
        message = MessageObject(name=name, payload=payload)
        result = message.to_dict()
        assert result["name"] == name

    @given(name=identifier_strategy, content_type=st.sampled_from(
        ["application/json", "application/xml", "text/plain"]
    ))
    @settings(max_examples=50)
    def test_content_type_in_dict(self, name: str, content_type: str):
        """Content type should be in to_dict."""
        payload = SchemaObject(schema_type="object")
        message = MessageObject(name=name, payload=payload, content_type=content_type)
        result = message.to_dict()
        assert result["contentType"] == content_type

    @given(name=identifier_strategy, correlation_id=identifier_strategy)
    @settings(max_examples=50)
    def test_correlation_id_in_dict(self, name: str, correlation_id: str):
        """Correlation ID should be in to_dict."""
        payload = SchemaObject(schema_type="object")
        message = MessageObject(
            name=name, payload=payload, correlation_id=correlation_id
        )
        result = message.to_dict()
        assert result["correlationId"]["location"] == correlation_id


class TestOperationObject:
    """Tests for OperationObject."""

    @given(
        action=st.sampled_from(["send", "receive"]),
        channel=identifier_strategy,
    )
    @settings(max_examples=50)
    def test_to_dict_contains_action(self, action: str, channel: str):
        """to_dict should contain the action."""
        operation = OperationObject(action=action, channel=channel)
        result = operation.to_dict()
        assert result["action"] == action

    @given(channel=identifier_strategy)
    @settings(max_examples=50)
    def test_channel_reference_format(self, channel: str):
        """Channel should be a reference."""
        operation = OperationObject(action="send", channel=channel)
        result = operation.to_dict()
        assert result["channel"]["$ref"] == f"#/channels/{channel}"


class TestChannelObject:
    """Tests for ChannelObject."""

    @given(address=identifier_strategy)
    @settings(max_examples=50)
    def test_to_dict_contains_address(self, address: str):
        """to_dict should contain the address."""
        channel = ChannelObject(address=address)
        result = channel.to_dict()
        assert result["address"] == address

    @given(address=identifier_strategy, description=st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_description_in_dict(self, address: str, description: str):
        """Description should be in to_dict."""
        channel = ChannelObject(address=address, description=description)
        result = channel.to_dict()
        assert result["description"] == description


class TestServerObject:
    """Tests for ServerObject."""

    @given(
        host=st.text(min_size=1, max_size=50),
        protocol=st.sampled_from(list(ProtocolType)),
    )
    @settings(max_examples=50)
    def test_to_dict_contains_host_and_protocol(
        self, host: str, protocol: ProtocolType
    ):
        """to_dict should contain host and protocol."""
        server = ServerObject(host=host, protocol=protocol)
        result = server.to_dict()
        assert result["host"] == host
        assert result["protocol"] == protocol.value


class TestInfoObject:
    """Tests for InfoObject."""

    @given(title=identifier_strategy, version=version_strategy)
    @settings(max_examples=50)
    def test_to_dict_contains_title_and_version(self, title: str, version: str):
        """to_dict should contain title and version."""
        info = InfoObject(title=title, version=version)
        result = info.to_dict()
        assert result["title"] == title
        assert result["version"] == version

    @given(
        title=identifier_strategy,
        version=version_strategy,
        contact_name=identifier_strategy,
        contact_email=st.emails(),
    )
    @settings(max_examples=50)
    def test_contact_in_dict(
        self, title: str, version: str, contact_name: str, contact_email: str
    ):
        """Contact should be in to_dict."""
        info = InfoObject(
            title=title,
            version=version,
            contact_name=contact_name,
            contact_email=contact_email,
        )
        result = info.to_dict()
        assert result["contact"]["name"] == contact_name
        assert result["contact"]["email"] == contact_email


class TestAsyncAPIDocument:
    """Tests for AsyncAPIDocument."""

    @given(title=identifier_strategy, version=version_strategy)
    @settings(max_examples=50)
    def test_to_dict_has_asyncapi_version(self, title: str, version: str):
        """to_dict should have asyncapi version."""
        info = InfoObject(title=title, version=version)
        doc = AsyncAPIDocument(info=info)
        result = doc.to_dict()
        assert result["asyncapi"] == "3.0.0"

    @given(title=identifier_strategy, version=version_strategy)
    @settings(max_examples=50)
    def test_to_json_is_valid_json(self, title: str, version: str):
        """to_json should produce valid JSON."""
        info = InfoObject(title=title, version=version)
        doc = AsyncAPIDocument(info=info)
        json_str = doc.to_json()
        parsed = json.loads(json_str)
        assert parsed["asyncapi"] == "3.0.0"

    @given(
        title=identifier_strategy,
        version=version_strategy,
        server_name=identifier_strategy,
        host=st.text(min_size=1, max_size=30),
    )
    @settings(max_examples=50)
    def test_add_server_fluent_api(
        self, title: str, version: str, server_name: str, host: str
    ):
        """add_server should return self for fluent API."""
        info = InfoObject(title=title, version=version)
        doc = AsyncAPIDocument(info=info)
        server = ServerObject(host=host, protocol=ProtocolType.KAFKA)
        result = doc.add_server(server_name, server)
        assert result is doc
        assert server_name in doc.servers

    @given(
        title=identifier_strategy,
        version=version_strategy,
        channel_name=identifier_strategy,
        address=identifier_strategy,
    )
    @settings(max_examples=50)
    def test_add_channel_fluent_api(
        self, title: str, version: str, channel_name: str, address: str
    ):
        """add_channel should return self for fluent API."""
        info = InfoObject(title=title, version=version)
        doc = AsyncAPIDocument(info=info)
        channel = ChannelObject(address=address)
        result = doc.add_channel(channel_name, channel)
        assert result is doc
        assert channel_name in doc.channels


class TestAsyncAPIBuilder:
    """Tests for AsyncAPIBuilder."""

    @given(title=identifier_strategy, version=version_strategy)
    @settings(max_examples=50)
    def test_build_creates_document(self, title: str, version: str):
        """build should create an AsyncAPIDocument."""
        builder = AsyncAPIBuilder(title=title, version=version)
        doc = builder.build()
        assert isinstance(doc, AsyncAPIDocument)
        assert doc.info.title == title
        assert doc.info.version == version

    @given(
        title=identifier_strategy,
        version=version_strategy,
        description=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=50)
    def test_with_description_sets_description(
        self, title: str, version: str, description: str
    ):
        """with_description should set the description."""
        builder = AsyncAPIBuilder(title=title, version=version)
        result = builder.with_description(description)
        assert result is builder
        doc = builder.build()
        assert doc.info.description == description

    @given(
        title=identifier_strategy,
        version=version_strategy,
        server_name=identifier_strategy,
        host=st.text(min_size=1, max_size=30),
    )
    @settings(max_examples=50)
    def test_add_kafka_server(
        self, title: str, version: str, server_name: str, host: str
    ):
        """add_kafka_server should add a Kafka server."""
        builder = AsyncAPIBuilder(title=title, version=version)
        builder.add_kafka_server(server_name, host)
        doc = builder.build()
        assert server_name in doc.servers
        assert doc.servers[server_name].protocol == ProtocolType.KAFKA


class TestFactoryFunctions:
    """Tests for factory functions."""

    @given(name=identifier_strategy)
    @settings(max_examples=50)
    def test_create_event_schema(self, name: str):
        """create_event_schema should create a schema."""
        schema = create_event_schema(
            name=name,
            properties={"id": "string", "timestamp": "datetime"},
            required=["id"],
        )
        assert schema.schema_type == "object"
        assert "id" in schema.properties
        assert "id" in schema.required

    @given(name=identifier_strategy)
    @settings(max_examples=50)
    def test_create_event_message(self, name: str):
        """create_event_message should create a message."""
        schema = SchemaObject(schema_type="object")
        message = create_event_message(name=name, schema=schema)
        assert message.name == name
        assert message.payload is schema
