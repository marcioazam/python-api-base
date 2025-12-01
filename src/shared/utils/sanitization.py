"""Input sanitization utilities to prevent injection attacks."""

import html
import logging
import re
from enum import Enum
from typing import Any


def sanitize_string(value: str, *, strip_html: bool = True) -> str:
    """Sanitize a string value.

    Removes or escapes potentially dangerous characters to prevent
    XSS and injection attacks.

    Args:
        value: String to sanitize.
        strip_html: If True, escape HTML entities.

    Returns:
        str: Sanitized string.
    """
    if not value:
        return value

    # Strip leading/trailing whitespace
    result = value.strip()

    # Escape HTML entities if requested
    if strip_html:
        result = html.escape(result)

    # Remove null bytes
    result = result.replace("\x00", "")

    return result


def sanitize_sql_identifier(value: str) -> str:
    """Sanitize a SQL identifier (table name, column name).

    Only allows alphanumeric characters and underscores.

    Args:
        value: Identifier to sanitize.

    Returns:
        str: Sanitized identifier.

    Raises:
        ValueError: If identifier is empty after sanitization.
    """
    if not value:
        raise ValueError("SQL identifier cannot be empty")

    # Only allow alphanumeric and underscore
    result = re.sub(r"[^a-zA-Z0-9_]", "", value)

    if not result:
        raise ValueError("SQL identifier contains no valid characters")

    # Ensure it doesn't start with a number
    if result[0].isdigit():
        result = "_" + result

    return result


def sanitize_path(value: str) -> str:
    """Sanitize a file path to prevent path traversal attacks.

    Args:
        value: Path to sanitize.

    Returns:
        str: Sanitized path.
    """
    if not value:
        return value

    # Remove path traversal sequences
    result = value.replace("..", "")
    result = result.replace("//", "/")

    # Remove null bytes
    result = result.replace("\x00", "")

    # Remove leading slashes to prevent absolute paths
    result = result.lstrip("/\\")

    return result


def sanitize_dict(data: dict[str, Any], *, recursive: bool = True) -> dict[str, Any]:
    """Sanitize all string values in a dictionary.

    Args:
        data: Dictionary to sanitize.
        recursive: If True, recursively sanitize nested dicts.

    Returns:
        dict: Dictionary with sanitized string values.
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = sanitize_string(value)
        elif isinstance(value, dict) and recursive:
            result[key] = sanitize_dict(value, recursive=True)
        elif isinstance(value, list):
            result[key] = [
                sanitize_string(item) if isinstance(item, str)
                else sanitize_dict(item, recursive=True) if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def strip_dangerous_chars(value: str) -> str:
    """Remove characters commonly used in injection attacks.

    Args:
        value: String to clean.

    Returns:
        str: Cleaned string.
    """
    if not value:
        return value

    # Characters often used in SQL injection
    dangerous_chars = [";", "--", "/*", "*/", "@@", "@", "char(", "nchar("]

    result = value
    for char in dangerous_chars:
        result = result.replace(char, "")

    return result


# --- Extended Sanitization (api-base-improvements) ---


class SanitizationType(str, Enum):
    """Types of sanitization to apply.

    **Feature: api-base-improvements**
    **Validates: Requirements 7.1, 7.2**
    """

    HTML = "html"
    SQL = "sql"
    SHELL = "shell"
    PATH = "path"
    ALL = "all"


class InputSanitizer:
    """Comprehensive input sanitizer with logging.

    **Feature: api-base-improvements**
    **Validates: Requirements 7.1, 7.2, 7.4**
    """

    # HTML dangerous patterns
    HTML_PATTERNS = [
        "<script", "</script>", "javascript:", "onerror=", "onload=",
        "onclick=", "onmouseover=", "<iframe", "<object", "<embed",
    ]

    # SQL injection patterns
    SQL_PATTERNS = [
        "' OR ", "' AND ", "'; DROP", "'; DELETE", "'; UPDATE",
        "'; INSERT", "UNION SELECT", "/*", "*/", "--", "@@",
        "EXEC ", "EXECUTE ", "xp_", "sp_",
    ]

    # Shell injection patterns
    SHELL_PATTERNS = [
        ";", "|", "&", "`", "$(",  "$(", "&&", "||",
        ">", "<", ">>", "<<", "\n", "\r",
    ]

    def __init__(self, log_modifications: bool = True) -> None:
        """Initialize sanitizer.

        Args:
            log_modifications: Whether to log when input is modified.
        """
        self._log_modifications = log_modifications
        self._logger = logging.getLogger(__name__)

    def sanitize(
        self,
        value: str,
        types: list[SanitizationType] | None = None,
    ) -> str:
        """Sanitize input with specified sanitization types.

        Args:
            value: Input string to sanitize.
            types: List of sanitization types to apply.

        Returns:
            Sanitized string.
        """
        if not value:
            return value

        types = types or [SanitizationType.ALL]
        original = value
        result = value

        if SanitizationType.ALL in types or SanitizationType.HTML in types:
            result = self.sanitize_html(result)

        if SanitizationType.ALL in types or SanitizationType.SQL in types:
            result = self.sanitize_sql(result)

        if SanitizationType.ALL in types or SanitizationType.SHELL in types:
            result = self.sanitize_shell(result)

        if SanitizationType.ALL in types or SanitizationType.PATH in types:
            result = sanitize_path(result)

        if self._log_modifications and result != original:
            self._logger.warning(
                "Input sanitized",
                extra={
                    "original_length": len(original),
                    "sanitized_length": len(result),
                    "types": [t.value for t in types],
                },
            )

        return result

    def sanitize_html(self, value: str) -> str:
        """Sanitize HTML/XSS patterns.

        Args:
            value: Input string.

        Returns:
            Sanitized string with HTML entities escaped.
        """
        if not value:
            return value

        # Escape HTML entities
        result = html.escape(value)

        # Remove dangerous patterns (case-insensitive)
        lower_result = result.lower()
        for pattern in self.HTML_PATTERNS:
            if pattern.lower() in lower_result:
                result = re.sub(
                    re.escape(pattern),
                    "",
                    result,
                    flags=re.IGNORECASE,
                )
                lower_result = result.lower()

        return result

    def sanitize_sql(self, value: str) -> str:
        """Sanitize SQL injection patterns.

        Args:
            value: Input string.

        Returns:
            Sanitized string with SQL patterns removed.
        """
        if not value:
            return value

        result = value

        # Remove SQL injection patterns (case-insensitive)
        for pattern in self.SQL_PATTERNS:
            result = re.sub(
                re.escape(pattern),
                "",
                result,
                flags=re.IGNORECASE,
            )

        return result

    def sanitize_shell(self, value: str) -> str:
        """Sanitize shell injection patterns.

        Args:
            value: Input string.

        Returns:
            Sanitized string with shell metacharacters removed.
        """
        if not value:
            return value

        result = value

        for pattern in self.SHELL_PATTERNS:
            result = result.replace(pattern, "")

        return result

    def is_safe(self, value: str, types: list[SanitizationType] | None = None) -> bool:
        """Check if input is safe (no sanitization needed).

        Args:
            value: Input to check.
            types: Sanitization types to check against.

        Returns:
            True if input is already safe.
        """
        return self.sanitize(value, types) == value


# Module-level sanitizer instance
_default_sanitizer: InputSanitizer | None = None


def get_sanitizer() -> InputSanitizer:
    """Get the default sanitizer instance."""
    global _default_sanitizer
    if _default_sanitizer is None:
        _default_sanitizer = InputSanitizer()
    return _default_sanitizer
