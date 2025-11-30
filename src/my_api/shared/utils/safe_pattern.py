"""Safe regex pattern compilation with ReDoS prevention.

**Feature: shared-modules-security-fixes**
**Validates: Requirements 4.1, 4.2, 4.3**
"""

from __future__ import annotations

import re
from functools import lru_cache
from re import Pattern

from my_api.shared.exceptions import PatternValidationError


# Maximum pattern length to prevent abuse
MAX_PATTERN_LENGTH = 1000

# Dangerous patterns that can cause ReDoS
DANGEROUS_PATTERNS = [
    r"\(\.\+\)\+",      # (.+)+
    r"\(\.\*\)\*",      # (.*)*
    r"\(\.\+\)\*",      # (.+)*
    r"\(\.\*\)\+",      # (.*)+
    r"\(\[\^[^\]]+\]\+\)\+",  # ([^x]+)+
    r"\(\[\^[^\]]+\]\*\)\+",  # ([^x]*)+
    r"\(\[\^[^\]]+\]\+\)\*",  # ([^x]+)*
]


class SafePatternCompiler:
    """Compile regex patterns safely with ReDoS prevention.

    This class provides safe regex compilation by:
    1. Validating pattern length
    2. Detecting dangerous nested quantifier patterns
    3. Providing safe glob-to-regex conversion
    """

    @classmethod
    def compile(
        cls,
        pattern: str,
        flags: int = 0,
        validate: bool = True,
    ) -> Pattern[str]:
        """Compile pattern with safety checks.

        Args:
            pattern: Regex pattern to compile.
            flags: Regex flags (re.IGNORECASE, etc.).
            validate: Whether to validate for dangerous patterns.

        Returns:
            Compiled regex pattern.

        Raises:
            PatternValidationError: If pattern is invalid or dangerous.
        """
        if validate:
            cls._validate_pattern(pattern)

        try:
            return re.compile(pattern, flags)
        except re.error as e:
            raise PatternValidationError(pattern, f"Invalid regex syntax: {e}") from e


    @classmethod
    def _validate_pattern(cls, pattern: str) -> None:
        """Validate pattern for safety.

        Args:
            pattern: Pattern to validate.

        Raises:
            PatternValidationError: If pattern is invalid or dangerous.
        """
        # Check length
        if len(pattern) > MAX_PATTERN_LENGTH:
            raise PatternValidationError(
                pattern[:50] + "...",
                f"Pattern exceeds maximum length of {MAX_PATTERN_LENGTH} characters",
            )

        # Check for dangerous patterns
        for dangerous in DANGEROUS_PATTERNS:
            if re.search(dangerous, pattern):
                raise PatternValidationError(
                    pattern,
                    "Pattern contains dangerous nested quantifiers (potential ReDoS)",
                )

    @classmethod
    @lru_cache(maxsize=256)
    def glob_to_regex(cls, glob_pattern: str) -> str:
        """Convert glob pattern to regex, escaping special chars.

        This method safely converts glob patterns (using * and ?) to regex
        by first escaping all regex special characters, then converting
        glob wildcards.

        Args:
            glob_pattern: Glob pattern with * and ? wildcards.

        Returns:
            Safe regex pattern string.

        Example:
            >>> SafePatternCompiler.glob_to_regex("*.txt")
            '^.*\\.txt$'
            >>> SafePatternCompiler.glob_to_regex("file[1].py")
            '^file\\[1\\]\\.py$'
        """
        # First escape all regex special characters
        escaped = re.escape(glob_pattern)

        # Then convert glob wildcards (which are now escaped)
        # \* -> .* (match any characters)
        # \? -> . (match single character)
        escaped = escaped.replace(r"\*", ".*")
        escaped = escaped.replace(r"\?", ".")

        # Anchor the pattern
        return f"^{escaped}$"

    @classmethod
    def compile_glob(
        cls,
        glob_pattern: str,
        flags: int = 0,
    ) -> Pattern[str]:
        """Compile glob pattern as regex.

        Args:
            glob_pattern: Glob pattern with * and ? wildcards.
            flags: Regex flags.

        Returns:
            Compiled regex pattern.
        """
        regex_pattern = cls.glob_to_regex(glob_pattern)
        # Skip dangerous pattern validation for glob-converted patterns
        # since they are safely escaped
        return re.compile(regex_pattern, flags)

    @classmethod
    def match_glob(cls, glob_pattern: str, text: str) -> bool:
        """Match text against glob pattern.

        Args:
            glob_pattern: Glob pattern with * and ? wildcards.
            text: Text to match.

        Returns:
            True if text matches pattern.
        """
        pattern = cls.compile_glob(glob_pattern)
        return pattern.match(text) is not None


# Convenience functions
def safe_compile(pattern: str, flags: int = 0) -> Pattern[str]:
    """Safely compile a regex pattern.

    Args:
        pattern: Regex pattern to compile.
        flags: Regex flags.

    Returns:
        Compiled regex pattern.

    Raises:
        PatternValidationError: If pattern is invalid or dangerous.
    """
    return SafePatternCompiler.compile(pattern, flags)


def glob_to_regex(glob_pattern: str) -> str:
    """Convert glob pattern to safe regex.

    Args:
        glob_pattern: Glob pattern with * and ? wildcards.

    Returns:
        Safe regex pattern string.
    """
    return SafePatternCompiler.glob_to_regex(glob_pattern)


def match_glob(glob_pattern: str, text: str) -> bool:
    """Match text against glob pattern.

    Args:
        glob_pattern: Glob pattern with * and ? wildcards.
        text: Text to match.

    Returns:
        True if text matches pattern.
    """
    return SafePatternCompiler.match_glob(glob_pattern, text)
