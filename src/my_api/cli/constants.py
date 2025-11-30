"""CLI constants and configuration.

**Feature: cli-security-improvements, Task 1.1: Constants Module**
**Validates: Requirements 1.1, 1.3, 2.1, 2.3, 3.3**
"""

import re
from typing import Final

# =============================================================================
# Timeouts
# =============================================================================

SUBPROCESS_TIMEOUT: Final[int] = 300  # 5 minutes default timeout

# =============================================================================
# Validation Patterns
# =============================================================================

REVISION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[a-zA-Z0-9_\-]+$|^head$|^base$"
)
"""Pattern for valid database revision identifiers."""

ENTITY_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]*$")
"""Pattern for valid entity names (snake_case, starts with letter)."""

FIELD_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]*$")
"""Pattern for valid field names (snake_case, starts with letter)."""

PATH_TRAVERSAL_PATTERN: Final[re.Pattern[str]] = re.compile(r"\.\.[\\/]|[\\/]\.\.")
"""Pattern to detect path traversal sequences."""

MARKER_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_\s,]+$")
"""Pattern for valid pytest markers."""

# =============================================================================
# Limits
# =============================================================================

MAX_ENTITY_NAME_LENGTH: Final[int] = 50
"""Maximum length for entity names."""

MAX_FIELD_NAME_LENGTH: Final[int] = 50
"""Maximum length for field names."""

MIN_ROLLBACK_STEPS: Final[int] = 1
"""Minimum number of rollback steps."""

MAX_ROLLBACK_STEPS: Final[int] = 100
"""Maximum number of rollback steps."""

# =============================================================================
# Whitelists
# =============================================================================

ALLOWED_ALEMBIC_COMMANDS: Final[frozenset[str]] = frozenset({
    "upgrade",
    "downgrade",
    "revision",
    "current",
    "history",
    "heads",
})
"""Allowed alembic commands for security."""

ALLOWED_FIELD_TYPES: Final[frozenset[str]] = frozenset({
    "str",
    "int",
    "float",
    "bool",
    "datetime",
    "date",
    "uuid",
    "list",
    "dict",
    "bytes",
    "Decimal",
})
"""Allowed field types for entity generation."""

# =============================================================================
# Exit Codes (Unix conventions)
# =============================================================================

EXIT_SUCCESS: Final[int] = 0
"""Successful execution."""

EXIT_ERROR: Final[int] = 1
"""General error."""

EXIT_MISUSE: Final[int] = 2
"""Command line usage error."""

EXIT_TIMEOUT: Final[int] = 124
"""Command timed out."""

EXIT_TERMINATED: Final[int] = 130
"""Command terminated by signal."""

# =============================================================================
# CLI Configuration
# =============================================================================

CLI_NAME: Final[str] = "api-cli"
"""CLI application name."""

CLI_DEFAULT_VERSION: Final[str] = "0.1.0-dev"
"""Default version when package metadata unavailable."""
