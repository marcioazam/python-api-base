"""graphql_federation service."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class KeyDirective:
    """@key directive for entity identification."""

    fields: str
    resolvable: bool = True

    def to_sdl(self) -> str:
        """Convert to SDL string."""
        if self.resolvable:
            return f'@key(fields: "{self.fields}")'
        return f'@key(fields: "{self.fields}", resolvable: false)'

@dataclass(frozen=True, slots=True)
class RequiresDirective:
    """@requires directive for field dependencies."""

    fields: str

    def to_sdl(self) -> str:
        """Convert to SDL string."""
        return f'@requires(fields: "{self.fields}")'

@dataclass(frozen=True, slots=True)
class ProvidesDirective:
    """@provides directive for field provisions."""

    fields: str

    def to_sdl(self) -> str:
        """Convert to SDL string."""
        return f'@provides(fields: "{self.fields}")'

@dataclass(frozen=True, slots=True)
class OverrideDirective:
    """@override directive for field overriding."""

    from_subgraph: str

    def to_sdl(self) -> str:
        """Convert to SDL string."""
        return f'@override(from: "{self.from_subgraph}")'

@runtime_checkable
class EntityResolver(Protocol):
    """Protocol for entity resolvers."""

    async def resolve(self, representations: list[dict[str, Any]]) -> list[Any]:
        """Resolve entity representations."""
        ...

@dataclass(slots=True)
class FederatedField:
    """Represents a federated field with directives."""

    name: str
    field_type: str
    external: bool = False
    requires: RequiresDirective | None = None
    provides: ProvidesDirective | None = None
    override: OverrideDirective | None = None
    shareable: bool = False
    inaccessible: bool = False

    def to_sdl(self) -> str:
        """Convert to SDL string."""
        directives: list[str] = []
        if self.external:
            directives.append("@external")
        if self.requires:
            directives.append(self.requires.to_sdl())
        if self.provides:
            directives.append(self.provides.to_sdl())
        if self.override:
            directives.append(self.override.to_sdl())
        if self.shareable:
            directives.append("@shareable")
        if self.inaccessible:
            directives.append("@inaccessible")

        directive_str = " ".join(directives)
        if directive_str:
            return f"  {self.name}: {self.field_type} {directive_str}"
        return f"  {self.name}: {self.field_type}"

@dataclass(slots=True)
class FederatedEntity:
    """Represents a federated entity type."""

    name: str
    keys: list[KeyDirective] = field(default_factory=list)
    fields: list[FederatedField] = field(default_factory=list)
    extends: bool = False
    shareable: bool = False

    def add_key(self, fields: str, resolvable: bool = True) -> "FederatedEntity":
        """Add a key directive."""
        self.keys.append(KeyDirective(fields=fields, resolvable=resolvable))
        return self

    def add_field(
        self,
        name: str,
        field_type: str,
        external: bool = False,
        requires: str | None = None,
        provides: str | None = None,
    ) -> "FederatedEntity":
        """Add a field to the entity."""
        self.fields.append(
            FederatedField(
                name=name,
                field_type=field_type,
                external=external,
                requires=RequiresDirective(requires) if requires else None,
                provides=ProvidesDirective(provides) if provides else None,
            )
        )
        return self

    def to_sdl(self) -> str:
        """Convert to SDL string."""
        lines: list[str] = []
        type_keyword = "extend type" if self.extends else "type"
        directives: list[str] = []

        for key in self.keys:
            directives.append(key.to_sdl())
        if self.shareable:
            directives.append("@shareable")

        directive_str = " ".join(directives)
        lines.append(f"{type_keyword} {self.name} {directive_str} {{")

        for f in self.fields:
            lines.append(f.to_sdl())

        lines.append("}")
        return "\n".join(lines)

@dataclass(slots=True)
class Subgraph:
    """Represents a federated subgraph."""

    name: str
    url: str
    entities: list[FederatedEntity] = field(default_factory=list)
    resolvers: dict[str, EntityResolver] = field(default_factory=dict)

    def add_entity(self, entity: FederatedEntity) -> "Subgraph":
        """Add an entity to the subgraph."""
        self.entities.append(entity)
        return self

    def register_resolver(
        self, entity_name: str, resolver: EntityResolver
    ) -> "Subgraph":
        """Register an entity resolver."""
        self.resolvers[entity_name] = resolver
        return self

    def to_sdl(self) -> str:
        """Generate SDL for the subgraph."""
        lines: list[str] = [
            'extend schema @link(url: "https://specs.apollo.dev/federation/v2.0")',
            "",
        ]
        for entity in self.entities:
            lines.append(entity.to_sdl())
            lines.append("")
        return "\n".join(lines)

@dataclass(slots=True)
class FederatedSchema:
    """Manages federated schema composition."""

    subgraphs: dict[str, Subgraph] = field(default_factory=dict)

    def add_subgraph(self, subgraph: Subgraph) -> "FederatedSchema":
        """Add a subgraph to the federation."""
        self.subgraphs[subgraph.name] = subgraph
        return self

    def remove_subgraph(self, name: str) -> bool:
        """Remove a subgraph from the federation."""
        if name in self.subgraphs:
            del self.subgraphs[name]
            return True
        return False

    def get_subgraph(self, name: str) -> Subgraph | None:
        """Get a subgraph by name."""
        return self.subgraphs.get(name)

    def list_entities(self) -> list[str]:
        """List all entity names across subgraphs."""
        entities: set[str] = set()
        for subgraph in self.subgraphs.values():
            for entity in subgraph.entities:
                entities.add(entity.name)
        return sorted(entities)

    def get_entity_subgraphs(self, entity_name: str) -> list[str]:
        """Get subgraphs that define an entity."""
        result: list[str] = []
        for name, subgraph in self.subgraphs.items():
            for entity in subgraph.entities:
                if entity.name == entity_name:
                    result.append(name)
                    break
        return result

    async def resolve_entity(
        self, entity_name: str, representations: list[dict[str, Any]]
    ) -> list[Any]:
        """Resolve entity representations across subgraphs."""
        for subgraph in self.subgraphs.values():
            if entity_name in subgraph.resolvers:
                return await subgraph.resolvers[entity_name].resolve(representations)
        return []

    def compose(self) -> str:
        """Compose all subgraph schemas into supergraph SDL."""
        lines: list[str] = [
            "# Composed Supergraph Schema",
            "# Generated by FederatedSchema",
            "",
        ]
        for name, subgraph in self.subgraphs.items():
            lines.append(f"# Subgraph: {name} ({subgraph.url})")
            lines.append(subgraph.to_sdl())
        return "\n".join(lines)

    def validate(self) -> list[str]:
        """Validate federation schema for common issues."""
        errors: list[str] = []

        for name, subgraph in self.subgraphs.items():
            for entity in subgraph.entities:
                if not entity.keys:
                    errors.append(
                        f"Entity '{entity.name}' in subgraph '{name}' has no @key"
                    )
                for f in entity.fields:
                    if f.requires and not f.external:
                        if not any(
                            ef.name == f.requires.fields and ef.external
                            for ef in entity.fields
                        ):
                            errors.append(
                                f"Field '{f.name}' in '{entity.name}' requires "
                                f"'{f.requires.fields}' but it's not marked @external"
                            )
        return errors

class ReferenceResolver[T]:
    """Generic reference resolver for federated entities."""

    def __init__(self, entity_type: type[T], key_field: str = "id"):
        self.entity_type = entity_type
        self.key_field = key_field
        self._cache: dict[str, T] = {}

    def cache_entity(self, key: str, entity: T) -> None:
        """Cache an entity for resolution."""
        self._cache[key] = entity

    def clear_cache(self) -> None:
        """Clear the entity cache."""
        self._cache.clear()

    async def resolve(self, representations: list[dict[str, Any]]) -> list[T | None]:
        """Resolve representations to entities."""
        results: list[T | None] = []
        for rep in representations:
            key = str(rep.get(self.key_field, ""))
            entity = self._cache.get(key)
            results.append(entity)
        return results

@dataclass(slots=True)
class ServiceDefinition:
    """Service definition for federation introspection."""

    name: str
    url: str
    sdl: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {"name": self.name, "url": self.url, "sdl": self.sdl}

class FederationGateway:
    """Gateway for federated GraphQL services."""

    def __init__(self):
        self.services: dict[str, ServiceDefinition] = {}
        self.schema: FederatedSchema = FederatedSchema()

    def register_service(self, service: ServiceDefinition) -> None:
        """Register a service with the gateway."""
        self.services[service.name] = service

    def unregister_service(self, name: str) -> bool:
        """Unregister a service from the gateway."""
        if name in self.services:
            del self.services[name]
            self.schema.remove_subgraph(name)
            return True
        return False

    def get_service_sdl(self) -> dict[str, str]:
        """Get SDL for all registered services."""
        return {name: svc.sdl for name, svc in self.services.items()}

    def introspect(self) -> list[dict[str, str]]:
        """Introspect all registered services."""
        return [svc.to_dict() for svc in self.services.values()]

    async def execute_query(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
    ) -> dict[str, Any]:
        """Execute a federated query (stub for actual implementation)."""
        _ = query, variables, operation_name
        return {"data": None, "errors": [{"message": "Not implemented"}]}

def create_entity_type(
    name: str,
    key_fields: str,
    fields: list[tuple[str, str]],
    extends: bool = False,
) -> FederatedEntity:
    """Factory function to create a federated entity type."""
    entity = FederatedEntity(name=name, extends=extends)
    entity.add_key(key_fields)
    for field_name, field_type in fields:
        entity.add_field(field_name, field_type)
    return entity

def create_extended_entity(
    name: str,
    key_fields: str,
    external_fields: list[tuple[str, str]],
    local_fields: list[tuple[str, str, str | None]],
) -> FederatedEntity:
    """Create an extended entity with external and local fields."""
    entity = FederatedEntity(name=name, extends=True)
    entity.add_key(key_fields, resolvable=False)

    for field_name, field_type in external_fields:
        entity.add_field(field_name, field_type, external=True)

    for field_name, field_type, requires in local_fields:
        entity.add_field(field_name, field_type, requires=requires)

    return entity
