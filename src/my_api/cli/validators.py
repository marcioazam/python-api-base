"""CLI input validators.

**Feature: cli-security-improvements, Task 2.1: Validators Module**
**Validates: Requirements 1.3, 2.1, 2.3, 2.5, 2.6**
"""

from my_api.cli.constants import (
    ALLOWED_ALEMBIC_COMMANDS,
    ALLOWED_FIELD_TYPES,
    ENTITY_NAME_PATTERN,
    FIELD_NAME_PATTERN,
    MARKER_PATTERN,
    MAX_ENTITY_NAME_LENGTH,
    MAX_FIELD_NAME_LENGTH,
    MAX_ROLLBACK_STEPS,
    MIN_ROLLBACK_STEPS,
    PATH_TRAVERSAL_PATTERN,
    REVISION_PATTERN,
)
from my_api.cli.exceptions import (
    InvalidCommandError,
    InvalidEntityNameError,
    InvalidFieldError,
    InvalidPathError,
    InvalidRevisionError,
    ValidationError,
)


def validate_revision(revision: str) -> str:
    """Validate database revision format.

    Args:
        revision: Revision identifier to validate.

    Returns:
        The validated revision string.

    Raises:
        InvalidRevisionError: If revision format is invalid.
    """
    if not revision:
        raise InvalidRevisionError(revision)
    if not REVISION_PATTERN.match(revision):
        raise InvalidRevisionError(revision)
    return revision


def validate_entity_name(name: str) -> str:
    """Validate entity name format and length.

    Args:
        name: Entity name to validate.

    Returns:
        The validated entity name.

    Raises:
        InvalidEntityNameError: If name format or length is invalid.
    """
    if not name:
        raise InvalidEntityNameError(name, "name cannot be empty")
    if len(name) > MAX_ENTITY_NAME_LENGTH:
        raise InvalidEntityNameError(
            name, f"name exceeds {MAX_ENTITY_NAME_LENGTH} characters"
        )
    if not ENTITY_NAME_PATTERN.match(name):
        raise InvalidEntityNameError(
            name, "must be snake_case starting with lowercase letter"
        )
    return name


def validate_path(path: str) -> str:
    """Validate path does not contain traversal sequences.

    Args:
        path: File path to validate.

    Returns:
        The validated path.

    Raises:
        InvalidPathError: If path contains traversal sequences.
    """
    if not path:
        raise InvalidPathError(path, "path cannot be empty")
    if PATH_TRAVERSAL_PATTERN.search(path):
        raise InvalidPathError(path, "path traversal detected")
    return path


def validate_alembic_command(command: str) -> str:
    """Validate alembic command against whitelist.

    Args:
        command: Alembic command to validate.

    Returns:
        The validated command.

    Raises:
        InvalidCommandError: If command is not in whitelist.
    """
    if not command:
        raise InvalidCommandError(command, ALLOWED_ALEMBIC_COMMANDS)
    if command not in ALLOWED_ALEMBIC_COMMANDS:
        raise InvalidCommandError(command, ALLOWED_ALEMBIC_COMMANDS)
    return command


def validate_field_definition(field_str: str) -> tuple[str, str]:
    """Validate and parse field definition.

    Args:
        field_str: Field definition in format "name:type".

    Returns:
        Tuple of (field_name, field_type).

    Raises:
        InvalidFieldError: If field format, name, or type is invalid.
    """
    if not field_str or not field_str.strip():
        raise InvalidFieldError(field_str, "field definition cannot be empty")

    parts = field_str.strip().split(":")
    if len(parts) != 2:
        raise InvalidFieldError(field_str, "must be in format 'name:type'")

    name, ftype = parts[0].strip(), parts[1].strip()

    if not name:
        raise InvalidFieldError(field_str, "field name cannot be empty")
    if not ftype:
        raise InvalidFieldError(field_str, "field type cannot be empty")

    if not FIELD_NAME_PATTERN.match(name):
        raise InvalidFieldError(
            field_str, f"field name '{name}' must be snake_case"
        )
    if len(name) > MAX_FIELD_NAME_LENGTH:
        raise InvalidFieldError(
            field_str, f"field name exceeds {MAX_FIELD_NAME_LENGTH} characters"
        )
    if ftype not in ALLOWED_FIELD_TYPES:
        allowed = ", ".join(sorted(ALLOWED_FIELD_TYPES))
        raise InvalidFieldError(
            field_str, f"type '{ftype}' not allowed. Use: {allowed}"
        )

    return name, ftype


def validate_rollback_steps(steps: int) -> int:
    """Validate rollback steps count.

    Args:
        steps: Number of steps to rollback.

    Returns:
        The validated steps count.

    Raises:
        ValidationError: If steps is out of valid range.
    """
    if steps < MIN_ROLLBACK_STEPS:
        raise ValidationError(
            f"Rollback steps must be at least {MIN_ROLLBACK_STEPS}"
        )
    if steps > MAX_ROLLBACK_STEPS:
        raise ValidationError(
            f"Rollback steps cannot exceed {MAX_ROLLBACK_STEPS}"
        )
    return steps


def validate_markers(markers: str) -> str:
    """Validate pytest markers string.

    Args:
        markers: Pytest markers expression.

    Returns:
        The validated markers string.

    Raises:
        ValidationError: If markers format is invalid.
    """
    if not markers:
        return markers  # Empty markers are allowed
    if not MARKER_PATTERN.match(markers):
        raise ValidationError(f"Invalid markers format: {markers}")
    return markers


def serialize_field_definition(name: str, ftype: str) -> str:
    """Serialize field definition back to string format.

    Args:
        name: Field name.
        ftype: Field type.

    Returns:
        Field definition string in format "name:type".
    """
    return f"{name}:{ftype}"
