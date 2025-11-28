"""Test execution commands.

**Feature: api-architecture-analysis, Task 10.1: CLI Tools**
**Validates: Requirements 10.1**
"""

import subprocess
import sys
from typing import Annotated

import typer

app = typer.Typer(help="Test execution commands")


def _run_pytest(args: list[str]) -> int:
    """Run pytest with given arguments."""
    cmd = [sys.executable, "-m", "pytest"] + args
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


@app.command()
def run(
    path: Annotated[str, typer.Argument(help="Test path or pattern")] = "tests/",
    coverage: Annotated[bool, typer.Option("--coverage", "-c", help="Run with coverage")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output")] = False,
    markers: Annotated[str, typer.Option("--markers", "-m", help="Run tests with specific markers")] = "",
    parallel: Annotated[bool, typer.Option("--parallel", "-p", help="Run tests in parallel")] = False,
) -> None:
    """Run tests."""
    args = [path]
    
    if coverage:
        args.extend(["--cov=src/my_api", "--cov-report=term-missing"])
    
    if verbose:
        args.append("-v")
    
    if markers:
        args.extend(["-m", markers])
    
    if parallel:
        args.extend(["-n", "auto"])
    
    typer.echo(f"Running tests: {' '.join(args)}")
    exit_code = _run_pytest(args)
    
    if exit_code == 0:
        typer.secho("✓ All tests passed", fg=typer.colors.GREEN)
    else:
        typer.secho("✗ Some tests failed", fg=typer.colors.RED)
        raise typer.Exit(code=exit_code)


@app.command()
def unit() -> None:
    """Run unit tests only."""
    typer.echo("Running unit tests...")
    exit_code = _run_pytest(["tests/unit/", "-v"])
    raise typer.Exit(code=exit_code)


@app.command()
def integration() -> None:
    """Run integration tests only."""
    typer.echo("Running integration tests...")
    exit_code = _run_pytest(["tests/integration/", "-v"])
    raise typer.Exit(code=exit_code)


@app.command()
def properties() -> None:
    """Run property-based tests only."""
    typer.echo("Running property-based tests...")
    exit_code = _run_pytest(["tests/properties/", "-v"])
    raise typer.Exit(code=exit_code)


@app.command()
def coverage() -> None:
    """Run all tests with coverage report."""
    typer.echo("Running tests with coverage...")
    args = [
        "tests/",
        "--cov=src/my_api",
        "--cov-report=term-missing",
        "--cov-report=html",
        "-v",
    ]
    exit_code = _run_pytest(args)
    
    if exit_code == 0:
        typer.secho("✓ Coverage report generated in htmlcov/", fg=typer.colors.GREEN)
    raise typer.Exit(code=exit_code)


@app.command()
def watch(
    path: Annotated[str, typer.Argument(help="Test path to watch")] = "tests/",
) -> None:
    """Run tests in watch mode (requires pytest-watch)."""
    typer.echo(f"Starting test watcher for: {path}")
    cmd = [sys.executable, "-m", "pytest_watch", "--", path, "-v"]
    subprocess.run(cmd)


@app.command()
def quick() -> None:
    """Run quick smoke tests."""
    typer.echo("Running quick smoke tests...")
    exit_code = _run_pytest([
        "tests/unit/",
        "-x",  # Stop on first failure
        "--tb=short",
        "-q",
    ])
    raise typer.Exit(code=exit_code)
