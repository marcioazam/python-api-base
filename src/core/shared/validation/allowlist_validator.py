"""Allowlist-based validation utilities.

**Feature: python-api-base-2025-validation**
**Validates: Requirements 36.1, 36.2, 36.5**

Provides generic allowlist validation following security best practices:
- Allowlist validation (not blocklist)
- Domain-specific validators (email, phone, URL, UUID)
- Result pattern integration
- Integration with core.base.patterns.validation.Validator protocol
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from uuid import UUID

from core.base.patterns.result import Err, Ok, Result
from core.base.patterns.validation import (
    CompositeValidator,
    FieldError,
    ValidationError,
)

if TYPE_CHECKING:
    pass


class AllowlistValidator[T](CompositeValidator[T]):
    """Generic allowlist validator implementing CompositeValidator protocol.

    Validates that values are in a predefined set of allowed values.
    This follows security best practices of allowlist (whitelist) validation
    rather than blocklist (blacklist) validation.

    Integrates with the core validation framework:
    - Implements CompositeValidator[T] for chaining support
    - Uses ValidationError[T] from core.base.patterns.validation
    - Supports and_then() and or_else() composition

    Type Parameters:
        T: Type of values to validate.

    Example:
        >>> validator = AllowlistValidator({"admin", "user", "guest"})
        >>> result = validator.validate("admin")
        >>> assert result.is_ok()
        >>> result = validator.validate("hacker")
        >>> assert result.is_err()

        # Chaining with other validators
        >>> from core.base.patterns.validation import NotEmptyValidator
        >>> chained = NotEmptyValidator().and_then(AllowlistValidator({"a", "b"}))

    **Feature: python-api-base-2025-validation**
    **Validates: Requirements 36.1, 36.2**
    """

    def __init__(
        self,
        allowed_values: set[T],
        field_name: str = "value",
        case_sensitive: bool = True,
    ) -> None:
        """Initialize allowlist validator.

        Args:
            allowed_values: Set of allowed values.
            field_name: Name of field for error messages.
            case_sensitive: Whether comparison is case-sensitive (for strings).
        """
        self._field_name = field_name
        self._case_sensitive = case_sensitive
        self._original_allowed = frozenset(allowed_values)

        if case_sensitive:
            self._allowed: set[T] = set(allowed_values)
        else:
            # Normalize to lowercase for case-insensitive comparison
            self._allowed = {
                v.lower() if isinstance(v, str) else v for v in allowed_values  # type: ignore[union-attr]
            }

    def validate(self, value: T) -> Result[T, ValidationError[T]]:
        """Validate that value is in allowlist.

        Args:
            value: Value to validate.

        Returns:
            Result with validated value or ValidationError.
        """
        check_value = value
        if not self._case_sensitive and isinstance(value, str):
            check_value = value.lower()  # type: ignore[assignment]

        if check_value in self._allowed:
            return Ok(value)

        return Err(
            ValidationError(
                message=f"Value '{value}' is not in allowed list for {self._field_name}",
                errors=[
                    FieldError(
                        field=self._field_name,
                        message=f"Value '{value}' is not allowed",
                        code="allowlist_violation",
                        value=value,
                    )
                ],
                context=value,
            )
        )

    def is_allowed(self, value: T) -> bool:
        """Check if value is in allowlist.

        Args:
            value: Value to check.

        Returns:
            True if allowed, False otherwise.
        """
        return self.validate(value).is_ok()

    def add(self, value: T) -> None:
        """Add value to allowlist.

        Args:
            value: Value to add.
        """
        if not self._case_sensitive and isinstance(value, str):
            self._allowed.add(value.lower())  # type: ignore[arg-type]
        else:
            self._allowed.add(value)

    def remove(self, value: T) -> None:
        """Remove value from allowlist.

        Args:
            value: Value to remove.
        """
        if not self._case_sensitive and isinstance(value, str):
            self._allowed.discard(value.lower())  # type: ignore[arg-type]
        else:
            self._allowed.discard(value)

    @property
    def allowed_values(self) -> frozenset[T]:
        """Get immutable copy of allowed values."""
        return frozenset(self._allowed)


# =============================================================================
# Domain-Specific Validators
# =============================================================================

# Email regex pattern (simplified but effective)
_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

# Phone regex pattern (international format)
_PHONE_PATTERN = re.compile(
    r"^\+?[1-9]\d{1,14}$"
)

# URL regex pattern
_URL_PATTERN = re.compile(
    r"^(https?|ftp)://[^\s/$.?#].[^\s]*$",
    re.IGNORECASE,
)


def validate_email(
    value: str, field_name: str = "email"
) -> Result[str, ValidationError[str]]:
    """Validate email address format.

    Args:
        value: Email address to validate.
        field_name: Field name for error messages.

    Returns:
        Result with validated email or ValidationError.

    **Feature: python-api-base-2025-validation**
    **Validates: Requirements 36.5**
    """
    if not value or not isinstance(value, str):
        return Err(
            ValidationError(
                message="Email is required",
                errors=[
                    FieldError(
                        field=field_name, message="Email is required", code="required"
                    )
                ],
                context=value if isinstance(value, str) else "",
            )
        )

    normalized = value.strip().lower()

    if not _EMAIL_PATTERN.match(normalized):
        return Err(
            ValidationError(
                message="Invalid email format",
                errors=[
                    FieldError(
                        field=field_name,
                        message="Invalid email format",
                        code="invalid_format",
                        value=value,
                    )
                ],
                context=value,
            )
        )

    # RFC 5321 limits
    if len(normalized) > 254:
        return Err(
            ValidationError(
                message="Email too long (max 254 characters)",
                errors=[
                    FieldError(
                        field=field_name,
                        message="Email exceeds maximum length of 254 characters",
                        code="max_length",
                        value=value,
                    )
                ],
                context=value,
            )
        )

    local_part = normalized.split("@")[0]
    if len(local_part) > 64:
        return Err(
            ValidationError(
                message="Email local part too long (max 64 characters)",
                errors=[
                    FieldError(
                        field=field_name,
                        message="Email local part exceeds maximum length of 64 characters",
                        code="max_length",
                        value=value,
                    )
                ],
                context=value,
            )
        )

    return Ok(normalized)


def validate_phone(
    value: str,
    field_name: str = "phone",
) -> Result[str, ValidationError[str]]:
    """Validate phone number format (E.164 international format).

    Args:
        value: Phone number to validate.
        field_name: Field name for error messages.

    Returns:
        Result with validated phone (cleaned) or ValidationError.

    **Feature: python-api-base-2025-validation**
    **Validates: Requirements 36.5**
    """
    if not value or not isinstance(value, str):
        return Err(
            ValidationError(
                message="Phone number is required",
                errors=[
                    FieldError(
                        field=field_name,
                        message="Phone number is required",
                        code="required",
                    )
                ],
                context=value if isinstance(value, str) else "",
            )
        )

    # Remove common formatting characters
    cleaned = re.sub(r"[\s\-\(\)\.]", "", value)

    if not _PHONE_PATTERN.match(cleaned):
        return Err(
            ValidationError(
                message="Invalid phone number format",
                errors=[
                    FieldError(
                        field=field_name,
                        message="Invalid phone number format (use E.164: +1234567890)",
                        code="invalid_format",
                        value=value,
                    )
                ],
                context=value,
            )
        )

    return Ok(cleaned)


def validate_url(
    value: str,
    field_name: str = "url",
    allowed_schemes: frozenset[str] | None = None,
) -> Result[str, ValidationError[str]]:
    """Validate URL format with scheme allowlist.

    Args:
        value: URL to validate.
        field_name: Field name for error messages.
        allowed_schemes: Set of allowed URL schemes (default: {"https"}).

    Returns:
        Result with validated URL or ValidationError.

    **Feature: python-api-base-2025-validation**
    **Validates: Requirements 36.5**
    """
    if allowed_schemes is None:
        allowed_schemes = frozenset({"https"})

    if not value or not isinstance(value, str):
        return Err(
            ValidationError(
                message="URL is required",
                errors=[
                    FieldError(
                        field=field_name, message="URL is required", code="required"
                    )
                ],
                context=value if isinstance(value, str) else "",
            )
        )

    normalized = value.strip()

    if not _URL_PATTERN.match(normalized):
        return Err(
            ValidationError(
                message="Invalid URL format",
                errors=[
                    FieldError(
                        field=field_name,
                        message="Invalid URL format",
                        code="invalid_format",
                        value=value,
                    )
                ],
                context=value,
            )
        )

    # Check scheme against allowlist (security best practice)
    scheme = normalized.split("://")[0].lower()
    if scheme not in allowed_schemes:
        return Err(
            ValidationError(
                message=f"URL scheme '{scheme}' not allowed",
                errors=[
                    FieldError(
                        field=field_name,
                        message=f"URL scheme '{scheme}' not in allowed list: {sorted(allowed_schemes)}",
                        code="scheme_not_allowed",
                        value=value,
                    )
                ],
                context=value,
            )
        )

    return Ok(normalized)


def validate_uuid(
    value: str,
    field_name: str = "id",
) -> Result[UUID, ValidationError[str]]:
    """Validate UUID format.

    Args:
        value: UUID string to validate.
        field_name: Field name for error messages.

    Returns:
        Result with validated UUID object or ValidationError.

    **Feature: python-api-base-2025-validation**
    **Validates: Requirements 36.5**
    """
    if not value or not isinstance(value, str):
        return Err(
            ValidationError(
                message="UUID is required",
                errors=[
                    FieldError(
                        field=field_name, message="UUID is required", code="required"
                    )
                ],
                context=value if isinstance(value, str) else "",
            )
        )

    try:
        uuid_obj = UUID(value.strip())
        return Ok(uuid_obj)
    except ValueError:
        return Err(
            ValidationError(
                message="Invalid UUID format",
                errors=[
                    FieldError(
                        field=field_name,
                        message="Invalid UUID format",
                        code="invalid_format",
                        value=value,
                    )
                ],
                context=value,
            )
        )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Validator class
    "AllowlistValidator",
    # Domain validators
    "validate_email",
    "validate_phone",
    "validate_url",
    "validate_uuid",
    # Re-export from core for convenience
    "ValidationError",
    "FieldError",
]
