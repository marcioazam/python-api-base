"""Test execution commands.

**Feature: cli-security-improvements, Task 7.1: Refactor test.py**
**Validates: Requirements 1.1, 2.5, 4.1**
"""

import logging
import subprocess
import sys
from typing import Annotated, Final

import typer

from my_api.cli.exceptions import CLIError, CLITimeoutError, ValidationError
from my_api.cli.runner import run_pytest
from my_api.cli.validators import validate_markers, validate_path

logger: Final[logging.Logger] = logging.getLogger(__name__)

app = typer.Typer(help="Test execution commands")


def _handle_cli_error(error: CLIError) -> None:
    """Handle CLI errors with consistent output."""
    typer.secho(f"✗ {error}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=error.exit_code)


@app.command()
def run(
    path: Annotated[str, typer.Argument(help="Test path or pattern")] = "tests/",
    coverage: Annotated[
        bool, typer.Option("--coverage", "-c", help="Run with coverage")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Verbose output")
    ] = False,
    markers: Annotated[
        str, typer.Option("--markers", "-m", help="Run tests with specific markers")
    ] = "",
    parallel: Annotated[
        bool, typer.Option("--parallel", "-p", help="Run tests in parallel")
    ] = False,
) -> None:
    """Run tests."""
    logger.debug(f"run command called with path={path}, coverage={coverage}")

    # Validate inputs
    try:
        validated_path = validate_path(path)
        validated_markers = validate_markers(markers)
    except ValidationError as e:
        _handle_cli_error(e)
        return

    args = [validated_path]

    if coverage:
        args.extend(["--cov=src/my_api", "--cov-report=term-missing"])

    if verbose:
        args.append("-v")

    if validated_markers:
        args.extend(["-m", validated_markers])

    if parallel:
        args.extend(["-n", "auto"])

    typer.echo(f"Running tests: {' '.join(args)}")

    try:
        exit_code = run_pytest(args)

        if exit_code == 0:
            typer.secho("✓ All tests passed", fg=typer.colors.GREEN)
        else:
            typer.secho("✗ Some tests failed", fg=typer.colors.RED)
            raise typer.Exit(code=exit_code)
    except CLITimeoutError as e:
        _handle_cli_error(e)


@app.command()
def unit() -> None:
    """Run unit tests only."""
    logger.debug("unit command called")
    typer.echo("Running unit tests...")

    try:
        validated_path = validate_path("tests/unit/")
        exit_code = run_pytest([validated_path, "-v"])
        raise typer.Exit(code=exit_code)
    except CLIError as e:
        _handle_cli_error(e)


@app.command()
def integration() -> None:
    """Run integration tests only."""
    logger.debug("integration command called")
    typer.echo("Running integration tests...")

    try:
        validated_path = validate_path("tests/integration/")
        exit_code = run_pytest([validated_path, "-v"])
        raise typer.Exit(code=exit_code)
    except CLIError as e:
        _handle_cli_error(e)


@app.command()
def properties() -> None:
    """Run property-based tests only."""
    logger.debug("properties command called")
    typer.echo("Running property-based tests...")

    try:
        validated_path = validate_path("tests/properties/")
        exit_code = run_pytest([validated_path, "-v"])
        raise typer.Exit(code=exit_code)
    except CLIError as e:
        _handle_cli_error(e)


@app.command()
def coverage() -> None:
    """Run all tests with coverage report."""
    logger.debug("coverage command called")
    typer.echo("Running tests with coverage...")

    try:
        validated_path = validate_path("tests/")
        args = [
            validated_path,
            "--cov=src/my_api",
            "--cov-report=term-missing",
            "--cov-report=html",
            "-v",
        ]
        exit_code = run_pytest(args)

        if exit_code == 0:
            typer.secho("✓ Coverage report generated in htmlcov/", fg=typer.colors.GREEN)
        raise typer.Exit(code=exit_code)
    except CLIError as e:
        _handle_cli_error(e)


@app.command()
def watch(
    path: Annotated[str, typer.Argument(help="Test path to watch")] = "tests/",
) -> None:
    """Run tests in watch mode (requires pytest-watch)."""
    logger.debug(f"watch command called with path={path}")

    try:
        validated_path = validate_path(path)
    except ValidationError as e:
        _handle_cli_error(e)
        return

    typer.echo(f"Starting test watcher for: {validated_path}")
    typer.echo("Press Ctrl+C to stop watching.")

    cmd = [sys.executable, "-m", "pytest_watch", "--", validated_path, "-v"]
    logger.info(f"Starting watch mode: {' '.join(cmd)}")

    try:
        # Watch mode runs indefinitely, so no timeout
        subprocess.run(cmd, check=False)
    except KeyboardInterrupt:
        typer.echo("\nWatch mode stopped.")
    except FileNotFoundError:
        typer.secho(
            "✗ pytest-watch not installed. Run: pip install pytest-watch",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)


@app.command()
def quick() -> None:
    """Run quick smoke tests."""
    logger.debug("quick command called")
    typer.echo("Running quick smoke tests...")

    try:
        validated_path = validate_path("tests/unit/")
        exit_code = run_pytest([
            validated_path,
            "-x",  # Stop on first failure
            "--tb=short",
            "-q",
        ])
        raise typer.Exit(code=exit_code)
    except CLIError as e:
        _handle_cli_error(e)
