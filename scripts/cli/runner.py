"""CLI command runners.

Provides functions to run external commands like alembic and pytest.
"""

import subprocess
import sys
from typing import Final

from scripts.cli.exceptions import CLITimeoutError

DEFAULT_TIMEOUT: Final[int] = 300  # 5 minutes


def run_alembic(args: list[str], timeout: int = DEFAULT_TIMEOUT) -> int:
    """Run alembic command.

    Args:
        args: Alembic command arguments.
        timeout: Command timeout in seconds.

    Returns:
        Exit code from alembic.

    Raises:
        CLITimeoutError: If command times out.
    """
    cmd = [sys.executable, "-m", "alembic"] + args

    try:
        result = subprocess.run(
            cmd,
            timeout=timeout,
            check=False,
        )
        return result.returncode
    except subprocess.TimeoutExpired as e:
        raise CLITimeoutError(
            f"Alembic command timed out after {timeout}s"
        ) from e


def run_pytest(args: list[str], timeout: int = DEFAULT_TIMEOUT) -> int:
    """Run pytest command.

    Args:
        args: Pytest command arguments.
        timeout: Command timeout in seconds.

    Returns:
        Exit code from pytest.

    Raises:
        CLITimeoutError: If command times out.
    """
    cmd = [sys.executable, "-m", "pytest"] + args

    try:
        result = subprocess.run(
            cmd,
            timeout=timeout,
            check=False,
        )
        return result.returncode
    except subprocess.TimeoutExpired as e:
        raise CLITimeoutError(
            f"Pytest command timed out after {timeout}s"
        ) from e
