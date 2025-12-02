"""Password policy validation service - Re-export module.

**Feature: infrastructure-code-review**
**Refactored: 2025 - Eliminated duplication with auth/password_policy.py**

This module re-exports password validation components from the canonical
location in infrastructure.auth.password_policy for backward compatibility.
"""

# Re-export all components from canonical location
from infrastructure.auth.password_policy import (
    COMMON_PASSWORD_PENALTY,
    COMMON_PASSWORDS,
    LENGTH_BONUS_MULTIPLIER,
    MAX_LENGTH_BONUS,
    MAX_SCORE,
    SCORE_PER_REQUIREMENT,
    PasswordPolicy,
    PasswordValidationResult,
    PasswordValidator,
    get_password_validator,
)

__all__ = [
    "COMMON_PASSWORD_PENALTY",
    "COMMON_PASSWORDS",
    "LENGTH_BONUS_MULTIPLIER",
    "MAX_LENGTH_BONUS",
    "MAX_SCORE",
    "SCORE_PER_REQUIREMENT",
    "PasswordPolicy",
    "PasswordValidationResult",
    "PasswordValidator",
    "get_password_validator",
]
