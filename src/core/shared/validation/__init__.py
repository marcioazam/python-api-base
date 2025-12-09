"""Validation utilities for the application.

**Feature: api-best-practices-review-2025**
**Feature: python-api-base-2025-validation**

Provides:
- Allowlist validation (security best practice)
- Domain-specific validators (email, phone, URL, UUID)
- Pydantic V2 high-performance validation utilities
- Integration with core.base.patterns.validation framework
"""

from core.base.patterns.validation import (
    FieldError,
    ValidationError,
)
from core.shared.validation.allowlist_validator import (
    AllowlistValidator,
    validate_email,
    validate_phone,
    validate_url,
    validate_uuid,
)
from core.shared.validation.pydantic_v2 import (
    ComputedFieldExample,
    EmailStr,
    LowercaseStr,
    OptimizedBaseModel,
    StrippedStr,
    TypeAdapterCache,
    UppercaseStr,
    get_type_adapter,
    validate_bulk,
    validate_bulk_json,
    validate_json_fast,
)

__all__ = [
    # Core validation types (from core.base.patterns.validation)
    "ValidationError",
    "FieldError",
    # Allowlist validation
    "AllowlistValidator",
    "validate_email",
    "validate_phone",
    "validate_url",
    "validate_uuid",
    # Pydantic V2 utilities
    "ComputedFieldExample",
    "EmailStr",
    "LowercaseStr",
    "OptimizedBaseModel",
    "StrippedStr",
    "TypeAdapterCache",
    "UppercaseStr",
    "get_type_adapter",
    "validate_bulk",
    "validate_bulk_json",
    "validate_json_fast",
]
