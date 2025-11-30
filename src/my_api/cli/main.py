"""Main CLI application entry point.

**Feature: cli-security-improvements, Task 9.1-9.2: Main Module**
**Validates: Requirements 4.1, 4.3, 6.1, 6.2, 6.3**
"""

import logging
import sys
from importlib.metadata import PackageNotFoundError, version as pkg_version
from pathlib import Path
from typing import Final

import typer

from my_api.cli.commands import db, generate, test
from my_api.cli.constants import CLI_DEFAULT_VERSION, CLI_NAME

# Configure logging for CLI module
logger: Final[logging.Logger] = logging.getLogger(__name__)


def _configure_logging(debug: bool = False) -> None:
    """Configure logging for CLI operations.

    Args:
        debug: Enable debug level logging.
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )


def get_version() -> str:
    """Get CLI version from package metadata.

    Returns:
        Version string from package metadata, or fallback with "-dev" suffix.
    """
    try:
        return pkg_version("my-api")
    except PackageNotFoundError:
        logger.debug("Package metadata not found, using fallback version")
        return CLI_DEFAULT_VERSION


app = typer.Typer(
    name=CLI_NAME,
    help="CLI tools for my-api project management",
    no_args_is_help=True,
    add_completion=True,
)

# Register command groups
app.add_typer(generate.app, name="generate", help="Code generation commands")
app.add_typer(db.app, name="db", help="Database management commands")
app.add_typer(test.app, name="test", help="Test execution commands")


@app.callback()
def main_callback(
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging"),
) -> None:
    """CLI tools for my-api project management."""
    if debug:
        _configure_logging(debug=True)
        logger.debug("Debug logging enabled")


@app.command()
def version() -> None:
    """Show CLI version."""
    logger.debug("version command called")
    ver = get_version()
    typer.echo(f"{CLI_NAME} version: {ver}")


@app.command()
def info() -> None:
    """Show project information."""
    logger.debug("info command called")

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
        status = (
            typer.style("✓", fg=typer.colors.GREEN)
            if exists
            else typer.style("✗", fg=typer.colors.RED)
        )
        typer.echo(f"  {status} {name}")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
