"""CLI tools for my-api project management.

**Feature: cli-security-improvements, Task 10.1: Module Exports**

Provides commands for:
- Entity generation
- Database migrations
- Test execution
- Development utilities

Usage:
    api-cli --help
    api-cli generate entity product --fields "name:str,price:float"
    api-cli db migrate
    api-cli test run --coverage
"""

from my_api.cli.constants import (
    ALLOWED_ALEMBIC_COMMANDS,
    ALLOWED_FIELD_TYPES,
    CLI_DEFAULT_VERSION,
    CLI_NAME,
    EXIT_ERROR,
    EXIT_SUCCESS,
    EXIT_TIMEOUT,
    SUBPROCESS_TIMEOUT,
)
from my_api.cli.exceptions import (
    AlembicError,
    CLIError,
    CLITimeoutError,
    CommandError,
    InvalidCommandError,
    InvalidEntityNameError,
    InvalidFieldError,
    InvalidPathError,
    InvalidRevisionError,
    PytestError,
    ValidationError,
)
from my_api.cli.main import app, get_version
from my_api.cli.runner import run_alembic, run_pytest, run_subprocess
from my_api.cli.validators import (
    serialize_field_definition,
    validate_alembic_command,
    validate_entity_name,
    validate_field_definition,
    validate_markers,
    validate_path,
    validate_revision,
    validate_rollback_steps,
)

__all__ = [
    # Main app
    "app",
    "get_version",
    # Constants
    "ALLOWED_ALEMBIC_COMMANDS",
    "ALLOWED_FIELD_TYPES",
    "CLI_DEFAULT_VERSION",
    "CLI_NAME",
    "EXIT_ERROR",
    "EXIT_SUCCESS",
    "EXIT_TIMEOUT",
    "SUBPROCESS_TIMEOUT",
    # Exceptions
    "AlembicError",
    "CLIError",
    "CLITimeoutError",
    "CommandError",
    "InvalidCommandError",
    "InvalidEntityNameError",
    "InvalidFieldError",
    "InvalidPathError",
    "InvalidRevisionError",
    "PytestError",
    "ValidationError",
    # Runner
    "run_alembic",
    "run_pytest",
    "run_subprocess",
    # Validators
    "serialize_field_definition",
    "validate_alembic_command",
    "validate_entity_name",
    "validate_field_definition",
    "validate_markers",
    "validate_path",
    "validate_revision",
    "validate_rollback_steps",
]
