"""Code generation commands.

**Feature: cli-security-improvements, Task 6.1-6.2: Refactor generate.py**
**Validates: Requirements 2.3, 2.4, 2.6, 5.1, 5.2, 5.3, 5.4**
"""

import logging
import re
from pathlib import Path
from typing import Annotated, Final

import typer

from my_api.cli.exceptions import CLIError, InvalidFieldError, ValidationError
from my_api.cli.validators import validate_entity_name, validate_field_definition

logger: Final[logging.Logger] = logging.getLogger(__name__)

app = typer.Typer(help="Code generation commands")


def _handle_cli_error(error: CLIError) -> None:
    """Handle CLI errors with consistent output."""
    typer.secho(f"✗ {error}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=error.exit_code)


def to_pascal_case(name: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in name.split("_"))


def to_snake_case(name: str) -> str:
    """Convert PascalCase to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def parse_fields(fields_str: str) -> list[tuple[str, str]]:
    """Parse and validate field definitions from string.

    Args:
        fields_str: Comma-separated field definitions.

    Returns:
        List of (name, type) tuples.

    Raises:
        InvalidFieldError: If any field definition is invalid.
    """
    if not fields_str or not fields_str.strip():
        return []

    fields: list[tuple[str, str]] = []
    for field in fields_str.split(","):
        field = field.strip()
        if field:
            name, ftype = validate_field_definition(field)
            fields.append((name, ftype))

    return fields


def _generate_entity_content(name: str, fields: list[tuple[str, str]]) -> str:
    """Generate entity file content with best practices.

    Uses UTC timezone for datetime fields (Requirement 5.1).
    Follows PEP8 import ordering (Requirement 5.2).
    """
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

    # PEP8 import ordering: stdlib, third-party, local
    return f'''"""{pascal_name} domain entity."""

from datetime import UTC, datetime

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
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime, nullable=False),
        description="Creation timestamp",
    )
    updated_at: datetime = SQLField(
        default_factory=lambda: datetime.now(UTC),
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
    """Generate routes file content with DI pattern (Requirement 5.3).

    Uses dependency injection instead of global instances.
    Includes TODO comments for required configuration (Requirement 5.4).
    """
    pascal_name = to_pascal_case(name)
    return f'''"""{pascal_name} API routes."""

from typing import Annotated

from fastapi import Depends

from my_api.application.mappers.{name}_mapper import {pascal_name}Mapper
from my_api.application.use_cases.{name}_use_case import {pascal_name}UseCase
from my_api.domain.entities.{name} import (
    {pascal_name}Create,
    {pascal_name}Response,
    {pascal_name}Update,
)
from my_api.shared.router import GenericCRUDRouter

# TODO: Configure repository with proper database session from DI container
# from my_api.core.container import Container
# from my_api.infrastructure.repositories.{name}_repository import {pascal_name}Repository


def get_{name}_mapper() -> {pascal_name}Mapper:
    """Dependency to get {pascal_name}Mapper."""
    return {pascal_name}Mapper()


def get_{name}_use_case(
    mapper: Annotated[{pascal_name}Mapper, Depends(get_{name}_mapper)],
    # TODO: Inject repository from DI container
    # repository: Annotated[{pascal_name}Repository, Depends(Container.{name}_repository)],
) -> {pascal_name}UseCase:
    """Dependency to get {pascal_name}UseCase.

    TODO: Replace InMemoryRepository with actual repository implementation.
    """
    from my_api.shared.repository import InMemoryRepository
    from my_api.domain.entities.{name} import {pascal_name}

    # TODO: Remove this temporary in-memory repository
    repository = InMemoryRepository({pascal_name})
    return {pascal_name}UseCase(repository, mapper)


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
    fields: Annotated[
        str,
        typer.Option(
            "--fields", "-f", help="Field definitions (e.g., 'name:str,price:float')"
        ),
    ] = "",
    with_cache: Annotated[
        bool, typer.Option("--with-cache", help="Add caching to use case")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print without writing files")
    ] = False,
) -> None:
    """Generate a new entity with CRUD scaffolding."""
    logger.debug(f"entity command called with name={name}, fields={fields}")

    # Convert to snake_case first
    snake_name = to_snake_case(name)

    # Validate entity name
    try:
        validated_name = validate_entity_name(snake_name)
    except ValidationError as e:
        _handle_cli_error(e)
        return  # For type checker

    # Parse and validate fields
    try:
        parsed_fields = parse_fields(fields)
    except InvalidFieldError as e:
        _handle_cli_error(e)
        return  # For type checker

    pascal_name = to_pascal_case(validated_name)
    logger.info(f"Generating entity: {pascal_name}")

    base_path = Path("src/my_api")

    files: dict[Path, str] = {
        base_path
        / "domain"
        / "entities"
        / f"{validated_name}.py": _generate_entity_content(validated_name, parsed_fields),
        base_path
        / "application"
        / "mappers"
        / f"{validated_name}_mapper.py": _generate_mapper_content(validated_name),
        base_path
        / "application"
        / "use_cases"
        / f"{validated_name}_use_case.py": _generate_use_case_content(
            validated_name, with_cache
        ),
        base_path
        / "adapters"
        / "api"
        / "routes"
        / f"{validated_name}s.py": _generate_routes_content(validated_name),
    }

    for path, content in files.items():
        if dry_run:
            typer.echo(f"\n{'=' * 60}")
            typer.echo(f"FILE: {path}")
            typer.echo("=" * 60)
            typer.echo(content)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                typer.secho(
                    f"⚠️  Skipping {path} (already exists)", fg=typer.colors.YELLOW
                )
            else:
                path.write_text(content)
                typer.secho(f"✓ Created {path}", fg=typer.colors.GREEN)

    if not dry_run:
        typer.echo(f"\n✓ Entity '{pascal_name}' scaffolding complete!")
        typer.echo("\nNext steps:")
        typer.echo("  1. Add router to main.py")
        typer.echo(f"  2. Create migration: api-cli db revision -m 'add {validated_name}s'")
        typer.echo("  3. Configure repository in DI container (see TODO comments)")
