#!/usr/bin/env python
"""Enhanced entity code generator for scaffolding new entities.

Usage:
    python scripts/generate_entity.py product
    python scripts/generate_entity.py order --fields "customer_id:str,total:float,status:str"
    python scripts/generate_entity.py order --with-events --with-cache
    python scripts/generate_entity.py --dry-run product

**Feature: advanced-reusability**
**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
"""

import argparse
import re
from pathlib import Path
from textwrap import dedent


def to_pascal_case(name: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in name.split("_"))


def to_snake_case(name: str) -> str:
    """Convert PascalCase to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def parse_fields(fields_str: str) -> list[tuple[str, str]]:
    """Parse field definitions from string."""
    if not fields_str:
        return []
    fields = []
    for field in fields_str.split(","):
        parts = field.strip().split(":")
        if len(parts) == 2:
            fields.append((parts[0].strip(), parts[1].strip()))
    return fields


def generate_entity(name: str, fields: list[tuple[str, str]]) -> str:
    """Generate entity file content."""
    pascal_name = to_pascal_case(name)
    
    if fields:
        field_lines = [
            f'{fname}: {ftype} = SQLField(description="{fname.replace("_", " ").title()}")'
            for fname, ftype in fields
        ]
        field_defs = "\n    ".join(field_lines)
        
        update_lines = [
            f"{fname}: {ftype} | None = SQLField(default=None)"
            for fname, ftype in fields
        ]
        update_fields = "\n    ".join(update_lines)
    else:
        field_defs = 'name: str = SQLField(min_length=1, max_length=255, description="Name")'
        update_fields = "name: str | None = SQLField(default=None, min_length=1, max_length=255)"

    return f'''"""{pascal_name} domain entity."""

from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from my_api.shared.utils.ids import generate_ulid


class {pascal_name}Base(SQLModel):
    """Base {name} fields shared between create/update/response."""

    {field_defs}


class {pascal_name}({pascal_name}Base, table=True):
    """{pascal_name} database model."""

    __tablename__ = "{name}s"

    id: str = SQLField(
        default_factory=generate_ulid,
        primary_key=True,
        description="ULID identifier",
    )
    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(),
        sa_column=Column(DateTime, nullable=False),
        description="Creation timestamp",
    )
    updated_at: datetime = SQLField(
        default_factory=lambda: datetime.now(),
        sa_column=Column(DateTime, nullable=False),
        description="Last update timestamp",
    )
    is_deleted: bool = SQLField(default=False, description="Soft delete flag")


class {pascal_name}Create({pascal_name}Base):
    """DTO for creating {name}s."""
    pass


class {pascal_name}Update(SQLModel):
    """DTO for updating {name}s (all fields optional)."""

    {update_fields}


class {pascal_name}Response({pascal_name}Base):
    """DTO for {name} responses."""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {{"from_attributes": True}}
'''


def generate_events(name: str) -> str:
    """Generate domain events file content."""
    pascal_name = to_pascal_case(name)
    return dedent(f'''
        """{pascal_name} domain events.

        Generated with --with-events flag.
        """

        from dataclasses import dataclass
        from datetime import datetime

        from my_api.shared.events import DomainEvent


        @dataclass(frozen=True)
        class {pascal_name}Created(DomainEvent):
            """Event emitted when a {name} is created."""

            {name}_id: str
            timestamp: datetime = None  # type: ignore

            def __post_init__(self):
                object.__setattr__(self, "timestamp", datetime.now())


        @dataclass(frozen=True)
        class {pascal_name}Updated(DomainEvent):
            """Event emitted when a {name} is updated."""

            {name}_id: str
            timestamp: datetime = None  # type: ignore

            def __post_init__(self):
                object.__setattr__(self, "timestamp", datetime.now())


        @dataclass(frozen=True)
        class {pascal_name}Deleted(DomainEvent):
            """Event emitted when a {name} is deleted."""

            {name}_id: str
            timestamp: datetime = None  # type: ignore

            def __post_init__(self):
                object.__setattr__(self, "timestamp", datetime.now())
    ''').strip()


def generate_mapper(name: str) -> str:
    """Generate mapper file content."""
    pascal_name = to_pascal_case(name)
    return dedent(f'''
        """{pascal_name} mapper implementation."""

        from my_api.domain.entities.{name} import {pascal_name}, {pascal_name}Response
        from my_api.shared.mapper import BaseMapper


        class {pascal_name}Mapper(BaseMapper[{pascal_name}, {pascal_name}Response]):
            """Mapper for {pascal_name} entity to response DTO."""

            def __init__(self) -> None:
                """Initialize mapper."""
                super().__init__({pascal_name}, {pascal_name}Response)
    ''').strip()


def generate_use_case(name: str, with_cache: bool = False) -> str:
    """Generate use case file content."""
    pascal_name = to_pascal_case(name)
    
    if with_cache:
        imports = f'''from my_api.domain.entities.{name} import (
    {pascal_name},
    {pascal_name}Create,
    {pascal_name}Response,
    {pascal_name}Update,
)
from my_api.shared.caching import cached
from my_api.shared.mapper import IMapper
from my_api.shared.repository import IRepository
from my_api.shared.use_case import BaseUseCase'''
        
        get_by_id_method = f'''

    @cached(ttl=300)
    async def get_by_id(self, entity_id: str) -> {pascal_name}Response | None:
        """Get {name} by ID (cached)."""
        return await super().get_by_id(entity_id)'''
    else:
        imports = f'''from my_api.domain.entities.{name} import (
    {pascal_name},
    {pascal_name}Create,
    {pascal_name}Response,
    {pascal_name}Update,
)
from my_api.shared.mapper import IMapper
from my_api.shared.repository import IRepository
from my_api.shared.use_case import BaseUseCase'''
        get_by_id_method = ""
    
    return f'''"""{pascal_name} use case implementation."""

{imports}


class {pascal_name}UseCase(
    BaseUseCase[{pascal_name}, {pascal_name}Create, {pascal_name}Update, {pascal_name}Response]
):
    """Use case for {pascal_name} operations."""

    def __init__(
        self,
        repository: IRepository[{pascal_name}, {pascal_name}Create, {pascal_name}Update],
        mapper: IMapper[{pascal_name}, {pascal_name}Response],
    ) -> None:
        """Initialize use case."""
        super().__init__(repository, mapper, entity_name="{pascal_name}"){get_by_id_method}
'''


def generate_routes(name: str) -> str:
    """Generate routes file content."""
    pascal_name = to_pascal_case(name)
    return dedent(f'''
        """{pascal_name} API routes."""

        from my_api.application.mappers.{name}_mapper import {pascal_name}Mapper
        from my_api.application.use_cases.{name}_use_case import {pascal_name}UseCase
        from my_api.domain.entities.{name} import (
            {pascal_name},
            {pascal_name}Create,
            {pascal_name}Response,
            {pascal_name}Update,
        )
        from my_api.shared.repository import InMemoryRepository
        from my_api.shared.router import GenericCRUDRouter


        # Singleton instances
        _{name}_mapper = {pascal_name}Mapper()
        _{name}_repository: InMemoryRepository[{pascal_name}, {pascal_name}Create, {pascal_name}Update] = (
            InMemoryRepository({pascal_name})
        )


        def get_{name}_use_case() -> {pascal_name}UseCase:
            """Dependency to get {pascal_name}UseCase."""
            return {pascal_name}UseCase(_{name}_repository, _{name}_mapper)


        # Create the generic CRUD router
        {name}_router = GenericCRUDRouter(
            prefix="/{name}s",
            tags=["{pascal_name}s"],
            response_model={pascal_name}Response,
            create_model={pascal_name}Create,
            update_model={pascal_name}Update,
            use_case_dependency=get_{name}_use_case,
        )

        router = {name}_router.router
    ''').strip()


def generate_property_tests(name: str, fields: list[tuple[str, str]]) -> str:
    """Generate property-based tests for the entity."""
    pascal_name = to_pascal_case(name)
    
    # Generate field strategies
    field_strategies = []
    for fname, ftype in fields:
        if ftype == "str":
            field_strategies.append(f'{fname}=st.text(min_size=1, max_size=100)')
        elif ftype == "int":
            field_strategies.append(f'{fname}=st.integers(min_value=0, max_value=10000)')
        elif ftype == "float":
            field_strategies.append(f'{fname}=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False)')
        elif ftype == "bool":
            field_strategies.append(f'{fname}=st.booleans()')
        else:
            field_strategies.append(f'{fname}=st.text(min_size=1, max_size=50)')
    
    if not field_strategies:
        field_strategies = ['name=st.text(min_size=1, max_size=100)']
    
    strategies_str = ",\n        ".join(field_strategies)

    return dedent(f'''
        """Property-based tests for {pascal_name} entity.

        Generated by scripts/generate_entity.py
        """

        from hypothesis import given, settings
        from hypothesis import strategies as st

        from my_api.domain.entities.{name} import (
            {pascal_name},
            {pascal_name}Create,
            {pascal_name}Response,
            {pascal_name}Update,
        )


        class Test{pascal_name}Properties:
            """Property tests for {pascal_name} entity."""

            @settings(max_examples=50)
            @given(
                {strategies_str}
            )
            def test_create_dto_round_trip(self, **kwargs) -> None:
                """
                For any valid {pascal_name}Create data, creating an entity
                and converting to response SHALL preserve all fields.
                """
                create_dto = {pascal_name}Create(**kwargs)
                
                # Verify all fields are set
                for key, value in kwargs.items():
                    assert getattr(create_dto, key) == value

            @settings(max_examples=50)
            @given(
                {strategies_str}
            )
            def test_update_dto_optional_fields(self, **kwargs) -> None:
                """
                {pascal_name}Update SHALL accept all fields as optional.
                """
                # All None should work
                update_dto = {pascal_name}Update()
                assert update_dto is not None
                
                # With values should work
                update_dto_with_values = {pascal_name}Update(**kwargs)
                for key, value in kwargs.items():
                    assert getattr(update_dto_with_values, key) == value

            @settings(max_examples=30)
            @given(
                {strategies_str}
            )
            def test_response_from_entity(self, **kwargs) -> None:
                """
                {pascal_name}Response SHALL be constructible from entity attributes.
                """
                from datetime import datetime
                
                response = {pascal_name}Response(
                    id="test-id",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    **kwargs
                )
                
                assert response.id == "test-id"
                for key, value in kwargs.items():
                    assert getattr(response, key) == value
    ''').strip()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate entity scaffolding")
    parser.add_argument("name", help="Entity name (snake_case)")
    parser.add_argument(
        "--fields",
        default="",
        help="Field definitions (e.g., 'name:str,price:float')",
    )
    parser.add_argument(
        "--with-events",
        action="store_true",
        help="Generate domain event classes for the entity",
    )
    parser.add_argument(
        "--with-cache",
        action="store_true",
        help="Add caching decorators to repository methods",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated code without writing files",
    )

    args = parser.parse_args()
    name = to_snake_case(args.name)
    fields = parse_fields(args.fields)
    pascal_name = to_pascal_case(name)

    # Define file paths
    base_path = Path(__file__).parent.parent / "src" / "my_api"
    test_path = Path(__file__).parent.parent / "tests" / "properties"

    files: dict[Path, str] = {
        base_path / "domain" / "entities" / f"{name}.py": generate_entity(name, fields),
        base_path / "application" / "mappers" / f"{name}_mapper.py": generate_mapper(name),
        base_path / "application" / "use_cases" / f"{name}_use_case.py": generate_use_case(name, args.with_cache),
        base_path / "adapters" / "api" / "routes" / f"{name}s.py": generate_routes(name),
        test_path / f"test_{name}_properties.py": generate_property_tests(name, fields),
    }

    # Add events if requested
    if args.with_events:
        files[base_path / "domain" / "events" / f"{name}_events.py"] = generate_events(name)

    for path, content in files.items():
        if args.dry_run:
            print(f"\n{'='*60}")
            print(f"FILE: {path}")
            print("="*60)
            print(content)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                print(f"⚠️  Skipping {path} (already exists)")
            else:
                path.write_text(content)
                print(f"✓ Created {path}")

    if not args.dry_run:
        print(f"\n✓ Entity '{name}' scaffolding complete!")
        print(f"\nGenerated files:")
        print(f"  - Entity: src/my_api/domain/entities/{name}.py")
        print(f"  - Mapper: src/my_api/application/mappers/{name}_mapper.py")
        print(f"  - Use Case: src/my_api/application/use_cases/{name}_use_case.py")
        print(f"  - Routes: src/my_api/adapters/api/routes/{name}s.py")
        print(f"  - Tests: tests/properties/test_{name}_properties.py")
        if args.with_events:
            print(f"  - Events: src/my_api/domain/events/{name}_events.py")
        print(f"\nNext steps:")
        print(f"  1. Review generated files")
        print(f"  2. Add router to main.py:")
        print(f"     from my_api.adapters.api.routes import {name}s")
        print(f"     app.include_router({name}s.router, prefix='/api/v1')")
        print(f"  3. Create Alembic migration:")
        print(f"     python scripts/migrate.py revision -m 'add {name}s table'")


if __name__ == "__main__":
    main()
