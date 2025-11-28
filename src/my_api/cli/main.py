"""Main CLI application entry point.

**Feature: api-architecture-analysis, Task 10.1: CLI Tools**
**Validates: Requirements 10.1**
"""

import typer

from my_api.cli.commands import db, generate, test

app = typer.Typer(
    name="api-cli",
    help="CLI tools for my-api project management",
    no_args_is_help=True,
    add_completion=True,
)

# Register command groups
app.add_typer(generate.app, name="generate", help="Code generation commands")
app.add_typer(db.app, name="db", help="Database management commands")
app.add_typer(test.app, name="test", help="Test execution commands")


@app.command()
def version() -> None:
    """Show CLI version."""
    typer.echo("api-cli version: 0.1.0")


@app.command()
def info() -> None:
    """Show project information."""
    import sys
    from pathlib import Path

    typer.echo("Project: my-api")
    typer.echo(f"Python: {sys.version}")
    typer.echo(f"Working Directory: {Path.cwd()}")
    
    # Check for key files
    checks = [
        ("pyproject.toml", Path("pyproject.toml").exists()),
        ("src/my_api", Path("src/my_api").exists()),
        ("tests", Path("tests").exists()),
        ("alembic.ini", Path("alembic.ini").exists()),
    ]
    
    typer.echo("\nProject Structure:")
    for name, exists in checks:
        status = typer.style("✓", fg=typer.colors.GREEN) if exists else typer.style("✗", fg=typer.colors.RED)
        typer.echo(f"  {status} {name}")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
