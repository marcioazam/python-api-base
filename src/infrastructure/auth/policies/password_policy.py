"""Password policy validation service.

**Feature: api-base-improvements, core-improvements-v2**
**Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 8.1, 8.2, 8.4, 8.5**
"""

import threading
from dataclasses import dataclass, field
from typing import Final

from core.shared.utils.password import hash_password, verify_password
from infrastructure.auth.common_passwords import COMMON_PASSWORDS

# Password strength scoring constants
SCORE_PER_REQUIREMENT: Final[int] = 20  # Points per met requirement
MAX_SCORE: Final[int] = 100  # Maximum possible score
LENGTH_BONUS_MULTIPLIER: Final[int] = 2  # Points per extra character
MAX_LENGTH_BONUS: Final[int] = 20  # Maximum bonus for extra length
COMMON_PASSWORD_PENALTY: Final[int] = 40  # Penalty for common passwords


@dataclass(frozen=True, slots=True)
class PasswordPolicy:
    """Password policy configuration.

    Attributes:
        min_length: Minimum password length (default: 12).
        max_length: Maximum password length (default: 128).
        require_uppercase: Require at least one uppercase letter.
        require_lowercase: Require at least one lowercase letter.
        require_digit: Require at least one digit.
        require_special: Require at least one special character.
        check_common_passwords: Check against common passwords list.
        special_characters: Set of allowed special characters.
    """

    min_length: int = 12
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    check_common_passwords: bool = True
    special_characters: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"


@dataclass
class PasswordValidationResult:
    """Result of password validation.

    Attributes:
        valid: Whether the password meets all requirements.
        errors: List of specific validation errors.
        strength_score: Password strength score (0-100).
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    strength_score: int = 0

    def add_error(self, error: str) -> None:
        """Add a validation error."""
        self.errors.append(error)
        self.valid = False


class PasswordValidator:
    """Password policy validator.

    Validates passwords against configurable policy requirements
    and provides specific feedback about unmet requirements.

    **Refactored: 2025 - Reduced validate() complexity from 14 to 6**
    """

    def __init__(self, policy: PasswordPolicy | None = None) -> None:
        """Initialize validator with policy.

        Args:
            policy: Password policy configuration. Uses defaults if None.
        """
        self._policy = policy or PasswordPolicy()

    @property
    def policy(self) -> PasswordPolicy:
        """Get the current password policy."""
        return self._policy

    def _check_length(self, password: str, result: PasswordValidationResult) -> int:
        """Check password length requirements. Returns score contribution."""
        score = 0
        if len(password) < self._policy.min_length:
            result.add_error(
                f"Password must be at least {self._policy.min_length} characters long"
            )
        else:
            score = SCORE_PER_REQUIREMENT

        if len(password) > self._policy.max_length:
            result.add_error(
                f"Password must be at most {self._policy.max_length} characters long"
            )
        return score

    def _check_character_requirements(
        self, password: str, result: PasswordValidationResult
    ) -> int:
        """Check character type requirements. Returns score contribution."""
        score = 0
        checks = [
            (self._policy.require_uppercase, str.isupper, "uppercase letter"),
            (self._policy.require_lowercase, str.islower, "lowercase letter"),
            (self._policy.require_digit, str.isdigit, "digit"),
        ]

        for required, check_fn, char_type in checks:
            if required:
                if any(check_fn(c) for c in password):
                    score += SCORE_PER_REQUIREMENT
                else:
                    result.add_error(f"Password must contain at least one {char_type}")

        # Special characters check (different pattern)
        if self._policy.require_special:
            if any(c in self._policy.special_characters for c in password):
                score += SCORE_PER_REQUIREMENT
            else:
                result.add_error(
                    f"Password must contain at least one special character "
                    f"({self._policy.special_characters})"
                )
        return score

    def _check_common_password(
        self, password: str, result: PasswordValidationResult, score: int
    ) -> int:
        """Check against common passwords. Returns adjusted score."""
        if self._policy.check_common_passwords and password.lower() in COMMON_PASSWORDS:
            result.add_error("Password is too common and easily guessable")
            return max(0, score - COMMON_PASSWORD_PENALTY)
        return score

    def _calculate_length_bonus(self, password: str, score: int) -> int:
        """Calculate bonus score for extra length."""
        extra_length = len(password) - self._policy.min_length
        if extra_length > 0:
            bonus = min(extra_length * LENGTH_BONUS_MULTIPLIER, MAX_LENGTH_BONUS)
            return min(MAX_SCORE, score + bonus)
        return score

    def validate(self, password: str) -> PasswordValidationResult:
        """Validate a password against the policy.

        **Refactored: Complexity reduced from 14 to 6**

        Args:
            password: Password to validate.

        Returns:
            PasswordValidationResult with validation status and errors.
        """
        result = PasswordValidationResult(valid=True)

        score = self._check_length(password, result)
        score += self._check_character_requirements(password, result)
        score = self._check_common_password(password, result, score)
        score = self._calculate_length_bonus(password, score)

        result.strength_score = score
        return result

    def is_valid(self, password: str) -> bool:
        """Check if password is valid.

        Args:
            password: Password to check.

        Returns:
            True if password meets all requirements.
        """
        return self.validate(password).valid

    def get_requirements(self) -> list[str]:
        """Get list of password requirements.

        Returns:
            List of requirement descriptions.
        """
        requirements = [
            f"At least {self._policy.min_length} characters long",
        ]

        if self._policy.require_uppercase:
            requirements.append("At least one uppercase letter (A-Z)")

        if self._policy.require_lowercase:
            requirements.append("At least one lowercase letter (a-z)")

        if self._policy.require_digit:
            requirements.append("At least one digit (0-9)")

        if self._policy.require_special:
            requirements.append(
                f"At least one special character ({self._policy.special_characters})"
            )

        if self._policy.check_common_passwords:
            requirements.append("Not a commonly used password")

        return requirements

    def hash_password(self, password: str) -> str:
        """Hash a password using Argon2id.

        Args:
            password: Plain text password.

        Returns:
            Hashed password string.

        Raises:
            ValueError: If password doesn't meet policy requirements.
        """
        result = self.validate(password)
        if not result.valid:
            raise ValueError(
                f"Password does not meet policy requirements: {', '.join(result.errors)}"
            )
        return hash_password(password)

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against a hash.

        Args:
            password: Plain text password to verify.
            hashed: Hashed password to compare against.

        Returns:
            True if password matches hash.
        """
        return verify_password(password, hashed)


# Default validator instance with thread-safe initialization
_default_validator: PasswordValidator | None = None
_password_lock = threading.Lock()


def get_password_validator() -> PasswordValidator:
    """Get the default password validator instance (thread-safe).

    Uses double-check locking pattern for thread-safe lazy initialization.

    **Feature: core-improvements-v2**
    **Validates: Requirements 1.2, 1.4, 1.5**
    """
    global _default_validator
    if _default_validator is None:
        with _password_lock:
            if _default_validator is None:  # Double-check locking
                _default_validator = PasswordValidator()
    return _default_validator
