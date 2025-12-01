"""CLI input validators.

Provides validation functions for CLI inputs.
"""

import re
from pathlib import Path

from scripts.cli.exceptions import InvalidFieldError, ValidationError

# Valid Python type annotations
VALID_TYPES: set[str] = {
    "str", "int", "float", "bool", "datetime", "date", "time",
    "list", "dict", "set", "tuple", "bytes", "Any", "None",
}

# Reserved Python keywords that cannot be used as names
RESERVED_KEYWORDS: set[str] = {
    "class", "def", "return", "if", "else", "elif", "for", "while",
    "try", "except", "finally", "with", "as", "import", "from",
    "pass", "break", "continue", "raise", "yield", "lambda", "and",
    "or", "not", "in", "is", "True", "False", "None", "global",
    "nonlocal", "assert", "del", "async", "await",
}


def validate_entity_name(name: str) -> str:
    """Validate entity name.

    Args:
        name: Entity name to validate.

    Returns:
        Validated entity name.

    Raises:
        ValidationError: If name is invalid.
    """
    if not name:
        raise ValidationError("Entity name cannot be empty")

    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        raise ValidationError(
            f"Invalid entity name '{name}'. "
            "Must be snake_case starting with a letter."
        )

    if name in RESERVED_KEYWORDS:
        raise ValidationError(f"'{name}' is a reserved Python keyword")

    return name


def validate_field_definition(field: str) -> tuple[str, str]:
    """Validate and parse field definition.

    Args:
        field: Field definition in format "name:type".

    Returns:
        Tuple of (field_name, field_type).

    Raises:
        InvalidFieldError: If field definition is invalid.
    """
    if ":" not in field:
        raise InvalidFieldError(
            f"Invalid field format '{field}'. Expected 'name:type'."
        )

    parts = field.split(":", 1)
    name = parts[0].strip()
    ftype = parts[1].strip()

    if not name:
        raise InvalidFieldError("Field name cannot be empty")

    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        raise InvalidFieldError(
            f"Invalid field name '{name}'. Must be snake_case."
        )

    if name in RESERVED_KEYWORDS:
        raise InvalidFieldError(f"'{name}' is a reserved Python keyword")

    # Extract base type for validation
    base_type = ftype.split("[")[0].strip()
    if base_type not in VALID_TYPES:
        raise InvalidFieldError(
            f"Unknown type '{ftype}'. Valid types: {', '.join(sorted(VALID_TYPES))}"
        )

    return name, ftype


def validate_revision(revision: str) -> str:
    """Validate migration revision.

    Args:
        revision: Revision identifier.

    Returns:
        Validated revision.

    Raises:
        ValidationError: If revision is invalid.
    """
    if not revision:
        raise ValidationError("Revision cannot be empty")

    # Allow 'head', 'base', or alphanumeric revision IDs
    if revision not in ("head", "base") and not re.match(r"^[a-f0-9]+$", revision):
        raise ValidationError(
            f"Invalid revision '{revision}'. "
            "Must be 'head', 'base', or a hex revision ID."
        )

    return revision


def validate_rollback_steps(steps: int) -> int:
    """Validate rollback steps.

    Args:
        steps: Number of steps to rollback.

    Returns:
        Validated steps.

    Raises:
        ValidationError: If steps is invalid.
    """
    if steps < 1:
        raise ValidationError("Rollback steps must be at least 1")

    if steps > 100:
        raise ValidationError("Rollback steps cannot exceed 100")

    return steps


def validate_alembic_command(command: str) -> str:
    """Validate alembic command.

    Args:
        command: Alembic command name.

    Returns:
        Validated command.

    Raises:
        ValidationError: If command is invalid.
    """
    valid_commands = {
        "upgrade", "downgrade", "revision", "current",
        "history", "heads", "branches", "show",
    }

    if command not in valid_commands:
        raise ValidationError(
            f"Invalid alembic command '{command}'. "
            f"Valid commands: {', '.join(sorted(valid_commands))}"
        )

    return command


def validate_path(path: str) -> str:
    """Validate file/directory path.

    Args:
        path: Path to validate.

    Returns:
        Validated path.

    Raises:
        ValidationError: If path is invalid.
    """
    if not path:
        raise ValidationError("Path cannot be empty")

    # Check for path traversal attempts
    if ".." in path:
        raise ValidationError("Path traversal not allowed")

    return path


def validate_markers(markers: str) -> str:
    """Validate pytest markers.

    Args:
        markers: Pytest marker expression.

    Returns:
        Validated markers.

    Raises:
        ValidationError: If markers are invalid.
    """
    if not markers:
        return ""

    # Basic validation - allow alphanumeric, spaces, and logical operators
    if not re.match(r"^[a-zA-Z0-9_\s\(\)]+(?:\s+(?:and|or|not)\s+[a-zA-Z0-9_\s\(\)]+)*$", markers):
        raise ValidationError(
            f"Invalid marker expression '{markers}'. "
            "Use alphanumeric markers with 'and', 'or', 'not' operators."
        )

    return markers
