"""Code generation commands.

**Feature: api-architecture-analysis, Task 10.1: CLI Tools**
**Validates: Requirements 10.1**
"""

import re
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(help="Code generation commands")


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


def _generate_entity_content(name: str, fields: list[tuple[str, str]]) -> str:
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


def _generate_mapper_content(name: str) -> str:
    """Generate mapper file content."""
    pascal_name = to_pascal_case(name)
    return f'''"""{pascal_name} mapper implementation."""

from my_api.domain.entities.{name} import {pascal_name}, {pascal_name}Response
from my_api.shared.mapper import BaseMapper


class {pascal_name}Mapper(BaseMapper[{pascal_name}, {pascal_name}Response]):
    """Mapper for {pascal_name} entity to response DTO."""

    def __init__(self) -> None:
        """Initialize mapper."""
        super().__init__({pascal_name}, {pascal_name}Response)
'''


def _generate_use_case_content(name: str, with_cache: bool = False) -> str:
    """Generate use case file content."""
    pascal_name = to_pascal_case(name)
    
    cache_import = "\nfrom my_api.shared.caching import cached" if with_cache else ""
    cache_decorator = "\n    @cached(ttl=300)" if with_cache else ""
    
    return f'''"""{pascal_name} use case implementation."""

from my_api.domain.entities.{name} import (
    {pascal_name},
    {pascal_name}Create,
    {pascal_name}Response,
    {pascal_name}Update,
)
from my_api.shared.mapper import IMapper
from my_api.shared.repository import IRepository
from my_api.shared.use_case import BaseUseCase{cache_import}


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
        super().__init__(repository, mapper, entity_name="{pascal_name}")
'''


def _generate_routes_content(name: str) -> str:
    """Generate routes file content."""
    pascal_name = to_pascal_case(name)
    return f'''"""{pascal_name} API routes."""

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


_{name}_mapper = {pascal_name}Mapper()
_{name}_repository: InMemoryRepository[{pascal_name}, {pascal_name}Create, {pascal_name}Update] = (
    InMemoryRepository({pascal_name})
)


def get_{name}_use_case() -> {pascal_name}UseCase:
    """Dependency to get {pascal_name}UseCase."""
    return {pascal_name}UseCase(_{name}_repository, _{name}_mapper)


{name}_router = GenericCRUDRouter(
    prefix="/{name}s",
    tags=["{pascal_name}s"],
    response_model={pascal_name}Response,
    create_model={pascal_name}Create,
    update_model={pascal_name}Update,
    use_case_dependency=get_{name}_use_case,
)

router = {name}_router.router
'''


@app.command()
def entity(
    name: Annotated[str, typer.Argument(help="Entity name (snake_case)")],
    fields: Annotated[str, typer.Option("--fields", "-f", help="Field definitions (e.g., 'name:str,price:float')")] = "",
    with_cache: Annotated[bool, typer.Option("--with-cache", help="Add caching to use case")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print without writing files")] = False,
) -> None:
    """Generate a new entity with CRUD scaffolding."""
    name = to_snake_case(name)
    parsed_fields = parse_fields(fields)
    pascal_name = to_pascal_case(name)
    
    base_path = Path("src/my_api")
    
    files: dict[Path, str] = {
        base_path / "domain" / "entities" / f"{name}.py": _generate_entity_content(name, parsed_fields),
        base_path / "application" / "mappers" / f"{name}_mapper.py": _generate_mapper_content(name),
        base_path / "application" / "use_cases" / f"{name}_use_case.py": _generate_use_case_content(name, with_cache),
        base_path / "adapters" / "api" / "routes" / f"{name}s.py": _generate_routes_content(name),
    }
    
    for path, content in files.items():
        if dry_run:
            typer.echo(f"\n{'='*60}")
            typer.echo(f"FILE: {path}")
            typer.echo("="*60)
            typer.echo(content)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                typer.secho(f"⚠️  Skipping {path} (already exists)", fg=typer.colors.YELLOW)
            else:
                path.write_text(content)
                typer.secho(f"✓ Created {path}", fg=typer.colors.GREEN)
    
    if not dry_run:
        typer.echo(f"\n✓ Entity '{pascal_name}' scaffolding complete!")
        typer.echo(f"\nNext steps:")
        typer.echo(f"  1. Add router to main.py")
        typer.echo(f"  2. Create migration: api-cli db revision -m 'add {name}s'")
