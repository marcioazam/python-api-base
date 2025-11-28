"""Property-based tests for GraphQL Federation.

**Feature: api-architecture-analysis, Property 1: Federation schema composition**
**Validates: Requirements 4.5**
"""

from hypothesis import given, settings, strategies as st

from my_api.shared.graphql_federation import (
    FederatedEntity,
    FederatedField,
    FederatedSchema,
    FederationGateway,
    KeyDirective,
    OverrideDirective,
    ProvidesDirective,
    ReferenceResolver,
    RequiresDirective,
    ServiceDefinition,
    Subgraph,
    create_entity_type,
    create_extended_entity,
)


identifier_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"),
    min_size=1,
    max_size=20,
)

graphql_type_strategy = st.sampled_from(
    ["String", "Int", "Float", "Boolean", "ID", "String!", "Int!", "[String]", "[Int!]!"]
)


class TestKeyDirective:
    """Tests for KeyDirective."""

    @given(fields=identifier_strategy, resolvable=st.booleans())
    @settings(max_examples=50)
    def test_key_directive_sdl_contains_fields(self, fields: str, resolvable: bool):
        """Key directive SDL should contain the fields."""
        directive = KeyDirective(fields=fields, resolvable=resolvable)
        sdl = directive.to_sdl()
        assert fields in sdl
        assert "@key" in sdl

    @given(fields=identifier_strategy)
    @settings(max_examples=50)
    def test_key_directive_resolvable_false_in_sdl(self, fields: str):
        """Non-resolvable key should include resolvable: false."""
        directive = KeyDirective(fields=fields, resolvable=False)
        sdl = directive.to_sdl()
        assert "resolvable: false" in sdl


class TestRequiresDirective:
    """Tests for RequiresDirective."""

    @given(fields=identifier_strategy)
    @settings(max_examples=50)
    def test_requires_directive_sdl_format(self, fields: str):
        """Requires directive should have correct SDL format."""
        directive = RequiresDirective(fields=fields)
        sdl = directive.to_sdl()
        assert f'@requires(fields: "{fields}")' == sdl


class TestProvidesDirective:
    """Tests for ProvidesDirective."""

    @given(fields=identifier_strategy)
    @settings(max_examples=50)
    def test_provides_directive_sdl_format(self, fields: str):
        """Provides directive should have correct SDL format."""
        directive = ProvidesDirective(fields=fields)
        sdl = directive.to_sdl()
        assert f'@provides(fields: "{fields}")' == sdl


class TestOverrideDirective:
    """Tests for OverrideDirective."""

    @given(from_subgraph=identifier_strategy)
    @settings(max_examples=50)
    def test_override_directive_sdl_format(self, from_subgraph: str):
        """Override directive should have correct SDL format."""
        directive = OverrideDirective(from_subgraph=from_subgraph)
        sdl = directive.to_sdl()
        assert f'@override(from: "{from_subgraph}")' == sdl


class TestFederatedField:
    """Tests for FederatedField."""

    @given(name=identifier_strategy, field_type=graphql_type_strategy)
    @settings(max_examples=50)
    def test_field_sdl_contains_name_and_type(self, name: str, field_type: str):
        """Field SDL should contain name and type."""
        field = FederatedField(name=name, field_type=field_type)
        sdl = field.to_sdl()
        assert name in sdl
        assert field_type in sdl

    @given(name=identifier_strategy, field_type=graphql_type_strategy)
    @settings(max_examples=50)
    def test_external_field_has_directive(self, name: str, field_type: str):
        """External field should have @external directive."""
        field = FederatedField(name=name, field_type=field_type, external=True)
        sdl = field.to_sdl()
        assert "@external" in sdl

    @given(name=identifier_strategy, field_type=graphql_type_strategy)
    @settings(max_examples=50)
    def test_shareable_field_has_directive(self, name: str, field_type: str):
        """Shareable field should have @shareable directive."""
        field = FederatedField(name=name, field_type=field_type, shareable=True)
        sdl = field.to_sdl()
        assert "@shareable" in sdl


class TestFederatedEntity:
    """Tests for FederatedEntity."""

    @given(name=identifier_strategy, key_fields=identifier_strategy)
    @settings(max_examples=50)
    def test_entity_sdl_contains_name(self, name: str, key_fields: str):
        """Entity SDL should contain the entity name."""
        entity = FederatedEntity(name=name)
        entity.add_key(key_fields)
        sdl = entity.to_sdl()
        assert name in sdl
        assert "@key" in sdl

    @given(name=identifier_strategy, key_fields=identifier_strategy)
    @settings(max_examples=50)
    def test_extended_entity_has_extend_keyword(self, name: str, key_fields: str):
        """Extended entity should have 'extend type' keyword."""
        entity = FederatedEntity(name=name, extends=True)
        entity.add_key(key_fields)
        sdl = entity.to_sdl()
        assert "extend type" in sdl

    @given(
        name=identifier_strategy,
        key_fields=identifier_strategy,
        field_name=identifier_strategy,
        field_type=graphql_type_strategy,
    )
    @settings(max_examples=50)
    def test_add_field_fluent_api(
        self, name: str, key_fields: str, field_name: str, field_type: str
    ):
        """add_field should return self for fluent API."""
        entity = FederatedEntity(name=name)
        result = entity.add_key(key_fields).add_field(field_name, field_type)
        assert result is entity
        assert len(entity.fields) == 1


class TestSubgraph:
    """Tests for Subgraph."""

    @given(name=identifier_strategy, url=st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_subgraph_sdl_has_federation_link(self, name: str, url: str):
        """Subgraph SDL should have federation link directive."""
        subgraph = Subgraph(name=name, url=url)
        sdl = subgraph.to_sdl()
        assert "@link" in sdl
        assert "federation" in sdl

    @given(
        subgraph_name=identifier_strategy,
        url=st.text(min_size=1, max_size=50),
        entity_name=identifier_strategy,
    )
    @settings(max_examples=50)
    def test_add_entity_fluent_api(
        self, subgraph_name: str, url: str, entity_name: str
    ):
        """add_entity should return self for fluent API."""
        subgraph = Subgraph(name=subgraph_name, url=url)
        entity = FederatedEntity(name=entity_name)
        result = subgraph.add_entity(entity)
        assert result is subgraph
        assert len(subgraph.entities) == 1


class TestFederatedSchema:
    """Tests for FederatedSchema."""

    @given(
        subgraph_name=identifier_strategy,
        url=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    def test_add_subgraph_stores_subgraph(self, subgraph_name: str, url: str):
        """add_subgraph should store the subgraph."""
        schema = FederatedSchema()
        subgraph = Subgraph(name=subgraph_name, url=url)
        schema.add_subgraph(subgraph)
        assert subgraph_name in schema.subgraphs
        assert schema.get_subgraph(subgraph_name) is subgraph

    @given(
        subgraph_name=identifier_strategy,
        url=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    def test_remove_subgraph_removes_subgraph(self, subgraph_name: str, url: str):
        """remove_subgraph should remove the subgraph."""
        schema = FederatedSchema()
        subgraph = Subgraph(name=subgraph_name, url=url)
        schema.add_subgraph(subgraph)
        result = schema.remove_subgraph(subgraph_name)
        assert result is True
        assert subgraph_name not in schema.subgraphs

    @given(name=identifier_strategy)
    @settings(max_examples=50)
    def test_remove_nonexistent_subgraph_returns_false(self, name: str):
        """remove_subgraph should return False for nonexistent subgraph."""
        schema = FederatedSchema()
        result = schema.remove_subgraph(name)
        assert result is False

    @given(
        subgraph_name=identifier_strategy,
        url=st.text(min_size=1, max_size=50),
        entity_name=identifier_strategy,
        key_fields=identifier_strategy,
    )
    @settings(max_examples=50)
    def test_list_entities_returns_all_entities(
        self, subgraph_name: str, url: str, entity_name: str, key_fields: str
    ):
        """list_entities should return all entity names."""
        schema = FederatedSchema()
        subgraph = Subgraph(name=subgraph_name, url=url)
        entity = FederatedEntity(name=entity_name)
        entity.add_key(key_fields)
        subgraph.add_entity(entity)
        schema.add_subgraph(subgraph)
        entities = schema.list_entities()
        assert entity_name in entities

    @given(
        subgraph_name=identifier_strategy,
        url=st.text(min_size=1, max_size=50),
        entity_name=identifier_strategy,
        key_fields=identifier_strategy,
    )
    @settings(max_examples=50)
    def test_get_entity_subgraphs(
        self, subgraph_name: str, url: str, entity_name: str, key_fields: str
    ):
        """get_entity_subgraphs should return subgraphs containing entity."""
        schema = FederatedSchema()
        subgraph = Subgraph(name=subgraph_name, url=url)
        entity = FederatedEntity(name=entity_name)
        entity.add_key(key_fields)
        subgraph.add_entity(entity)
        schema.add_subgraph(subgraph)
        subgraphs = schema.get_entity_subgraphs(entity_name)
        assert subgraph_name in subgraphs

    def test_compose_generates_supergraph_sdl(self):
        """compose should generate supergraph SDL."""
        schema = FederatedSchema()
        subgraph = Subgraph(name="users", url="http://users:4001/graphql")
        entity = FederatedEntity(name="User")
        entity.add_key("id").add_field("id", "ID!").add_field("name", "String!")
        subgraph.add_entity(entity)
        schema.add_subgraph(subgraph)
        sdl = schema.compose()
        assert "Composed Supergraph Schema" in sdl
        assert "users" in sdl


class TestReferenceResolver:
    """Tests for ReferenceResolver."""

    @given(key=identifier_strategy)
    @settings(max_examples=50)
    def test_cache_and_resolve(self, key: str):
        """Cached entity should be resolvable."""
        resolver: ReferenceResolver[dict[str, str]] = ReferenceResolver(
            dict, key_field="id"
        )
        entity = {"id": key, "name": "Test"}
        resolver.cache_entity(key, entity)
        assert resolver._cache[key] == entity

    def test_clear_cache(self):
        """clear_cache should empty the cache."""
        resolver: ReferenceResolver[dict[str, str]] = ReferenceResolver(
            dict, key_field="id"
        )
        resolver.cache_entity("1", {"id": "1"})
        resolver.clear_cache()
        assert len(resolver._cache) == 0


class TestServiceDefinition:
    """Tests for ServiceDefinition."""

    @given(
        name=identifier_strategy,
        url=st.text(min_size=1, max_size=50),
        sdl=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=50)
    def test_to_dict_contains_all_fields(self, name: str, url: str, sdl: str):
        """to_dict should contain all fields."""
        service = ServiceDefinition(name=name, url=url, sdl=sdl)
        result = service.to_dict()
        assert result["name"] == name
        assert result["url"] == url
        assert result["sdl"] == sdl


class TestFederationGateway:
    """Tests for FederationGateway."""

    @given(
        name=identifier_strategy,
        url=st.text(min_size=1, max_size=50),
        sdl=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=50)
    def test_register_service(self, name: str, url: str, sdl: str):
        """register_service should store the service."""
        gateway = FederationGateway()
        service = ServiceDefinition(name=name, url=url, sdl=sdl)
        gateway.register_service(service)
        assert name in gateway.services

    @given(
        name=identifier_strategy,
        url=st.text(min_size=1, max_size=50),
        sdl=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=50)
    def test_unregister_service(self, name: str, url: str, sdl: str):
        """unregister_service should remove the service."""
        gateway = FederationGateway()
        service = ServiceDefinition(name=name, url=url, sdl=sdl)
        gateway.register_service(service)
        result = gateway.unregister_service(name)
        assert result is True
        assert name not in gateway.services

    @given(name=identifier_strategy)
    @settings(max_examples=50)
    def test_unregister_nonexistent_service(self, name: str):
        """unregister_service should return False for nonexistent service."""
        gateway = FederationGateway()
        result = gateway.unregister_service(name)
        assert result is False

    def test_introspect_returns_all_services(self):
        """introspect should return all registered services."""
        gateway = FederationGateway()
        gateway.register_service(
            ServiceDefinition(name="svc1", url="http://svc1", sdl="type Query")
        )
        gateway.register_service(
            ServiceDefinition(name="svc2", url="http://svc2", sdl="type Query")
        )
        result = gateway.introspect()
        assert len(result) == 2


class TestFactoryFunctions:
    """Tests for factory functions."""

    @given(
        name=identifier_strategy,
        key_fields=identifier_strategy,
    )
    @settings(max_examples=50)
    def test_create_entity_type(self, name: str, key_fields: str):
        """create_entity_type should create entity with key."""
        entity = create_entity_type(
            name=name,
            key_fields=key_fields,
            fields=[("id", "ID!"), ("name", "String!")],
        )
        assert entity.name == name
        assert len(entity.keys) == 1
        assert len(entity.fields) == 2

    @given(
        name=identifier_strategy,
        key_fields=identifier_strategy,
    )
    @settings(max_examples=50)
    def test_create_extended_entity(self, name: str, key_fields: str):
        """create_extended_entity should create extended entity."""
        entity = create_extended_entity(
            name=name,
            key_fields=key_fields,
            external_fields=[("id", "ID!")],
            local_fields=[("reviews", "[Review!]!", "id")],
        )
        assert entity.name == name
        assert entity.extends is True
        assert len(entity.fields) == 2
