"""Database management commands.

**Feature: cli-security-improvements, Task 5.1: Refactor db.py**
**Validates: Requirements 1.1, 1.2, 1.3, 2.1, 4.1, 4.4**
"""

import logging
from typing import Annotated, Final

import typer

from my_api.cli.exceptions import CLIError, CLITimeoutError, ValidationError
from my_api.cli.runner import run_alembic
from my_api.cli.validators import (
    validate_alembic_command,
    validate_revision,
    validate_rollback_steps,
)

logger: Final[logging.Logger] = logging.getLogger(__name__)

app = typer.Typer(help="Database management commands")


def _handle_cli_error(error: CLIError) -> None:
    """Handle CLI errors with consistent output."""
    typer.secho(f"✗ {error}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=error.exit_code)


@app.command()
def migrate(
    revision: Annotated[
        str, typer.Option("--revision", "-r", help="Target revision")
    ] = "head",
) -> None:
    """Run database migrations to specified revision."""
    logger.debug(f"migrate command called with revision={revision}")

    try:
        validated_revision = validate_revision(revision)
        validate_alembic_command("upgrade")
    except ValidationError as e:
        _handle_cli_error(e)

    typer.echo(f"Running migrations to: {validated_revision}")

    try:
        exit_code = run_alembic(["upgrade", validated_revision])
        if exit_code == 0:
            typer.secho("✓ Migrations complete", fg=typer.colors.GREEN)
        else:
            typer.secho("✗ Migration failed", fg=typer.colors.RED)
            raise typer.Exit(code=exit_code)
    except CLITimeoutError as e:
        _handle_cli_error(e)


@app.command()
def rollback(
    steps: Annotated[
        int, typer.Option("--steps", "-n", help="Number of revisions to rollback")
    ] = 1,
) -> None:
    """Rollback database migrations."""
    logger.debug(f"rollback command called with steps={steps}")

    try:
        validated_steps = validate_rollback_steps(steps)
        validate_alembic_command("downgrade")
    except ValidationError as e:
        _handle_cli_error(e)

    revision = f"-{validated_steps}"
    typer.echo(f"Rolling back {validated_steps} revision(s)")

    try:
        exit_code = run_alembic(["downgrade", revision])
        if exit_code == 0:
            typer.secho("✓ Rollback complete", fg=typer.colors.GREEN)
        else:
            typer.secho("✗ Rollback failed", fg=typer.colors.RED)
            raise typer.Exit(code=exit_code)
    except CLITimeoutError as e:
        _handle_cli_error(e)


@app.command()
def revision(
    message: Annotated[
        str, typer.Option("--message", "-m", help="Revision message")
    ] = "auto",
    autogenerate: Annotated[
        bool, typer.Option("--autogenerate", "-a", help="Auto-generate from models")
    ] = True,
) -> None:
    """Create a new migration revision."""
    logger.debug(f"revision command called with message={message}")

    try:
        validate_alembic_command("revision")
    except ValidationError as e:
        _handle_cli_error(e)

    args = ["revision", "-m", message]
    if autogenerate:
        args.append("--autogenerate")

    typer.echo(f"Creating revision: {message}")

    try:
        exit_code = run_alembic(args)
        if exit_code == 0:
            typer.secho("✓ Revision created", fg=typer.colors.GREEN)
        else:
            typer.secho("✗ Revision creation failed", fg=typer.colors.RED)
            raise typer.Exit(code=exit_code)
    except CLITimeoutError as e:
        _handle_cli_error(e)


@app.command()
def current() -> None:
    """Show current database revision."""
    logger.debug("current command called")

    try:
        validate_alembic_command("current")
        run_alembic(["current"])
    except CLIError as e:
        _handle_cli_error(e)


@app.command()
def history(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show verbose output")
    ] = False,
) -> None:
    """Show migration history."""
    logger.debug(f"history command called with verbose={verbose}")

    try:
        validate_alembic_command("history")
    except ValidationError as e:
        _handle_cli_error(e)

    args = ["history"]
    if verbose:
        args.append("-v")

    try:
        run_alembic(args)
    except CLIError as e:
        _handle_cli_error(e)


@app.command()
def heads() -> None:
    """Show current available heads."""
    logger.debug("heads command called")

    try:
        validate_alembic_command("heads")
        run_alembic(["heads"])
    except CLIError as e:
        _handle_cli_error(e)


@app.command()
def reset(
    confirm: Annotated[
        bool, typer.Option("--yes", "-y", help="Skip confirmation")
    ] = False,
) -> None:
    """Reset database to initial state (DESTRUCTIVE)."""
    logger.warning("reset command called - DESTRUCTIVE OPERATION")

    if not confirm:
        confirm = typer.confirm("This will reset the database. Continue?")

    if not confirm:
        typer.echo("Cancelled")
        return

    logger.warning("Database reset confirmed by user")
    typer.echo("Resetting database...")

    try:
        validate_alembic_command("downgrade")
        validate_alembic_command("upgrade")

        exit_code = run_alembic(["downgrade", "base"])
        if exit_code == 0:
            exit_code = run_alembic(["upgrade", "head"])

        if exit_code == 0:
            typer.secho("✓ Database reset complete", fg=typer.colors.GREEN)
        else:
            typer.secho("✗ Database reset failed", fg=typer.colors.RED)
            raise typer.Exit(code=exit_code)
    except CLIError as e:
        _handle_cli_error(e)
