"""Database management commands.

**Feature: api-architecture-analysis, Task 10.1: CLI Tools**
**Validates: Requirements 10.1**
"""

import subprocess
import sys
from typing import Annotated

import typer

app = typer.Typer(help="Database management commands")


def _run_alembic(args: list[str]) -> int:
    """Run alembic command."""
    cmd = [sys.executable, "-m", "alembic"] + args
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


@app.command()
def migrate(
    revision: Annotated[str, typer.Option("--revision", "-r", help="Target revision")] = "head",
) -> None:
    """Run database migrations to specified revision."""
    typer.echo(f"Running migrations to: {revision}")
    exit_code = _run_alembic(["upgrade", revision])
    if exit_code == 0:
        typer.secho("✓ Migrations complete", fg=typer.colors.GREEN)
    else:
        typer.secho("✗ Migration failed", fg=typer.colors.RED)
        raise typer.Exit(code=exit_code)


@app.command()
def rollback(
    steps: Annotated[int, typer.Option("--steps", "-n", help="Number of revisions to rollback")] = 1,
) -> None:
    """Rollback database migrations."""
    revision = f"-{steps}"
    typer.echo(f"Rolling back {steps} revision(s)")
    exit_code = _run_alembic(["downgrade", revision])
    if exit_code == 0:
        typer.secho("✓ Rollback complete", fg=typer.colors.GREEN)
    else:
        typer.secho("✗ Rollback failed", fg=typer.colors.RED)
        raise typer.Exit(code=exit_code)


@app.command()
def revision(
    message: Annotated[str, typer.Option("--message", "-m", help="Revision message")] = "auto",
    autogenerate: Annotated[bool, typer.Option("--autogenerate", "-a", help="Auto-generate from models")] = True,
) -> None:
    """Create a new migration revision."""
    args = ["revision", "-m", message]
    if autogenerate:
        args.append("--autogenerate")
    
    typer.echo(f"Creating revision: {message}")
    exit_code = _run_alembic(args)
    if exit_code == 0:
        typer.secho("✓ Revision created", fg=typer.colors.GREEN)
    else:
        typer.secho("✗ Revision creation failed", fg=typer.colors.RED)
        raise typer.Exit(code=exit_code)


@app.command()
def current() -> None:
    """Show current database revision."""
    _run_alembic(["current"])


@app.command()
def history(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show verbose output")] = False,
) -> None:
    """Show migration history."""
    args = ["history"]
    if verbose:
        args.append("-v")
    _run_alembic(args)


@app.command()
def heads() -> None:
    """Show current available heads."""
    _run_alembic(["heads"])


@app.command()
def reset(
    confirm: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Reset database to initial state (DESTRUCTIVE)."""
    if not confirm:
        confirm = typer.confirm("This will reset the database. Continue?")
    
    if confirm:
        typer.echo("Resetting database...")
        exit_code = _run_alembic(["downgrade", "base"])
        if exit_code == 0:
            exit_code = _run_alembic(["upgrade", "head"])
        
        if exit_code == 0:
            typer.secho("✓ Database reset complete", fg=typer.colors.GREEN)
        else:
            typer.secho("✗ Database reset failed", fg=typer.colors.RED)
            raise typer.Exit(code=exit_code)
    else:
        typer.echo("Cancelled")
