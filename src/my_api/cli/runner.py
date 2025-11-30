"""Secure subprocess runner.

**Feature: cli-security-improvements, Task 3.1: Runner Module**
**Validates: Requirements 1.1, 1.2, 1.5, 4.2**
"""

import logging
import subprocess
import sys
from typing import Final

from my_api.cli.constants import SUBPROCESS_TIMEOUT
from my_api.cli.exceptions import CLITimeoutError, CommandError

logger: Final[logging.Logger] = logging.getLogger(__name__)


def run_subprocess(
    module: str,
    args: list[str],
    timeout: int = SUBPROCESS_TIMEOUT,
    capture_output: bool = False,
    check: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    """Run subprocess with security controls.

    Args:
        module: Python module to run (e.g., "alembic", "pytest").
        args: Arguments to pass to the module.
        timeout: Maximum execution time in seconds.
        capture_output: Whether to capture stdout/stderr.
        check: Whether to raise on non-zero exit code.

    Returns:
        CompletedProcess instance with execution results.

    Raises:
        CLITimeoutError: If command exceeds timeout.
        CommandError: If command execution fails.
    """
    cmd = [sys.executable, "-m", module] + args
    cmd_str = " ".join(cmd)

    logger.debug(f"Executing subprocess: {cmd_str}")
    logger.debug(f"Timeout: {timeout}s, capture_output: {capture_output}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            timeout=timeout,
            check=check,
        )
        logger.debug(f"Subprocess completed with return code: {result.returncode}")
        return result

    except subprocess.TimeoutExpired as e:
        logger.error(f"Subprocess timed out after {timeout}s: {cmd_str}")
        raise CLITimeoutError(cmd_str, timeout) from e

    except subprocess.CalledProcessError as e:
        logger.error(f"Subprocess failed with code {e.returncode}: {cmd_str}")
        raise CommandError(
            f"Command failed with exit code {e.returncode}",
            return_code=e.returncode,
        ) from e

    except FileNotFoundError as e:
        logger.error(f"Module not found: {module}")
        raise CommandError(f"Module not found: {module}") from e

    except Exception as e:
        logger.error(f"Subprocess execution failed: {e}", exc_info=True)
        raise CommandError(f"Command execution failed: {e}") from e


def run_alembic(
    args: list[str],
    timeout: int = SUBPROCESS_TIMEOUT,
) -> int:
    """Run alembic command with security controls.

    Args:
        args: Alembic command arguments.
        timeout: Maximum execution time in seconds.

    Returns:
        Process return code.

    Raises:
        CLITimeoutError: If command exceeds timeout.
        CommandError: If command execution fails.
    """
    logger.info(f"Running alembic: {' '.join(args)}")
    result = run_subprocess("alembic", args, timeout=timeout)
    return result.returncode


def run_pytest(
    args: list[str],
    timeout: int = SUBPROCESS_TIMEOUT,
) -> int:
    """Run pytest command with security controls.

    Args:
        args: Pytest command arguments.
        timeout: Maximum execution time in seconds.

    Returns:
        Process return code.

    Raises:
        CLITimeoutError: If command exceeds timeout.
        CommandError: If command execution fails.
    """
    logger.info(f"Running pytest: {' '.join(args)}")
    result = run_subprocess("pytest", args, timeout=timeout)
    return result.returncode
