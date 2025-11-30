"""Password policy validation service.

**Feature: api-base-improvements, core-improvements-v2**
**Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 8.1, 8.2, 8.4, 8.5**
"""

import threading
from dataclasses import dataclass, field
from typing import Final

from my_api.shared.utils.password import hash_password, verify_password

# Password strength scoring constants
SCORE_PER_REQUIREMENT: Final[int] = 20  # Points per met requirement
MAX_SCORE: Final[int] = 100  # Maximum possible score
LENGTH_BONUS_MULTIPLIER: Final[int] = 2  # Points per extra character
MAX_LENGTH_BONUS: Final[int] = 20  # Maximum bonus for extra length
COMMON_PASSWORD_PENALTY: Final[int] = 40  # Penalty for common passwords


# Common passwords list (top 100 most common)
COMMON_PASSWORDS = frozenset([
    "password", "123456", "12345678", "qwerty", "abc123",
    "monkey", "1234567", "letmein", "trustno1", "dragon",
    "baseball", "iloveyou", "master", "sunshine", "ashley",
    "bailey", "passw0rd", "shadow", "123123", "654321",
    "superman", "qazwsx", "michael", "football", "password1",
    "password123", "batman", "login", "admin", "welcome",
    "hello", "charlie", "donald", "password2", "qwerty123",
    "whatever", "freedom", "nothing", "secret", "princess",
    "starwars", "121212", "1234567890", "000000", "111111",
    "222222", "333333", "444444", "555555", "666666",
    "777777", "888888", "999999", "123321", "password!",
    "qwertyuiop", "asdfghjkl", "zxcvbnm", "1q2w3e4r", "1qaz2wsx",
    "abcd1234", "pass1234", "test1234", "user1234", "admin123",
    "root", "toor", "administrator", "guest", "default",
    "changeme", "temp", "test", "demo", "sample",
    "example", "public", "private", "secure", "security",
    "access", "system", "server", "database", "network",
    "internet", "intranet", "website", "webmaster", "support",
    "helpdesk", "service", "services", "backup", "restore",
    "recovery", "maintenance", "update", "upgrade", "install",
])


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

    def validate(self, password: str) -> PasswordValidationResult:
        """Validate a password against the policy.

        Args:
            password: Password to validate.

        Returns:
            PasswordValidationResult with validation status and errors.
        """
        result = PasswordValidationResult(valid=True)
        score = 0

        # Check minimum length
        if len(password) < self._policy.min_length:
            result.add_error(
                f"Password must be at least {self._policy.min_length} characters long"
            )
        else:
            score += SCORE_PER_REQUIREMENT

        # Check maximum length
        if len(password) > self._policy.max_length:
            result.add_error(
                f"Password must be at most {self._policy.max_length} characters long"
            )

        # Check uppercase requirement
        if self._policy.require_uppercase:
            if not any(c.isupper() for c in password):
                result.add_error("Password must contain at least one uppercase letter")
            else:
                score += SCORE_PER_REQUIREMENT

        # Check lowercase requirement
        if self._policy.require_lowercase:
            if not any(c.islower() for c in password):
                result.add_error("Password must contain at least one lowercase letter")
            else:
                score += SCORE_PER_REQUIREMENT

        # Check digit requirement
        if self._policy.require_digit:
            if not any(c.isdigit() for c in password):
                result.add_error("Password must contain at least one digit")
            else:
                score += SCORE_PER_REQUIREMENT

        # Check special character requirement
        if self._policy.require_special:
            if not any(c in self._policy.special_characters for c in password):
                result.add_error(
                    "Password must contain at least one special character "
                    f"({self._policy.special_characters})"
                )
            else:
                score += SCORE_PER_REQUIREMENT

        # Check against common passwords
        if self._policy.check_common_passwords:
            if password.lower() in COMMON_PASSWORDS:
                result.add_error("Password is too common and easily guessable")
                score = max(0, score - COMMON_PASSWORD_PENALTY)

        # Bonus for length beyond minimum
        extra_length = len(password) - self._policy.min_length
        if extra_length > 0:
            score = min(MAX_SCORE, score + min(extra_length * LENGTH_BONUS_MULTIPLIER, MAX_LENGTH_BONUS))

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
