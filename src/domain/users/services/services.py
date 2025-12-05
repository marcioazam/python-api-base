"""Domain services for the Users bounded context.

Domain services contain business logic that doesn't naturally fit
within a single entity or value object.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 2.5**
"""

import re
from typing import Protocol

# Email validation pattern (RFC 5322 simplified)
_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class PasswordHasher(Protocol):
    """Protocol for password hashing service."""

    def hash(self, password: str) -> str:
        """Hash a password."""
        ...

    def verify(self, password: str, hashed: str) -> bool:
        """Verify a password against a hash."""
        ...


class EmailValidator(Protocol):
    """Protocol for email validation service."""

    def is_valid(self, email: str) -> bool:
        """Check if email format is valid."""
        ...

    def is_disposable(self, email: str) -> bool:
        """Check if email is from a disposable provider."""
        ...


class UserDomainService:
    """Domain service for user-related operations.

    Contains business logic that spans multiple entities or
    requires external services.

    Example:
        ```python
        from domain.users.services import (
            UserDomainService,
            PasswordHasher,
            EmailValidator,
        )


        # Using default implementations (basic validation)
        class Argon2PasswordHasher:
            def hash(self, password: str) -> str:
                # Use argon2-cffi or similar
                return f"$argon2id$hashed_{password}"

            def verify(self, password: str, hashed: str) -> bool:
                expected = f"$argon2id$hashed_{password}"
                return hashed == expected


        hasher = Argon2PasswordHasher()
        service = UserDomainService(password_hasher=hasher)

        # Hash a password
        hashed = service.hash_password("SecurePass123!")
        print(hashed)  # "$argon2id$hashed_SecurePass123!"

        # Verify password
        is_valid = service.verify_password("SecurePass123!", hashed)
        print(is_valid)  # True

        # Validate password strength
        is_strong, errors = service.validate_password_strength("weak")
        if not is_strong:
            print("Password errors:", errors)
            # ['Password must be at least 8 characters',
            #  'Password must contain at least one uppercase letter',
            #  'Password must contain at least one digit',
            #  'Password must contain at least one special character']

        # Validate with strong password
        is_strong, errors = service.validate_password_strength("SecurePass123!")
        print(is_strong, errors)  # (True, [])

        # Basic email validation (no validator provided)
        is_valid, error = service.validate_email("user@example.com")
        print(is_valid, error)  # (True, None)

        is_valid, error = service.validate_email("invalid-email")
        print(is_valid, error)  # (False, "Invalid email format")
        ```

    Example with custom email validator:
        ```python
        class CustomEmailValidator:
            def is_valid(self, email: str) -> bool:
                return "@" in email and "." in email

            def is_disposable(self, email: str) -> bool:
                disposable_domains = ["tempmail.com", "10minutemail.com"]
                domain = email.split("@")[1] if "@" in email else ""
                return domain in disposable_domains


        validator = CustomEmailValidator()
        service = UserDomainService(
            password_hasher=Argon2PasswordHasher(), email_validator=validator
        )

        # Validate email with disposable check
        is_valid, error = service.validate_email("user@tempmail.com")
        print(is_valid, error)  # (False, "Disposable email addresses are not allowed")

        is_valid, error = service.validate_email("user@example.com")
        print(is_valid, error)  # (True, None)
        ```

    Example in User Registration Use Case:
        ```python
        from domain.users.aggregates import UserAggregate
        from domain.users.services import UserDomainService


        class RegisterUserUseCase:
            def __init__(self, user_domain_service: UserDomainService):
                self._domain_service = user_domain_service

            async def execute(self, email: str, password: str) -> UserAggregate:
                # 1. Validate email
                is_valid_email, email_error = self._domain_service.validate_email(email)
                if not is_valid_email:
                    raise ValueError(email_error)

                # 2. Validate password strength
                is_strong, password_errors = (
                    self._domain_service.validate_password_strength(password)
                )
                if not is_strong:
                    raise ValueError(f"Weak password: {', '.join(password_errors)}")

                # 3. Hash password
                password_hash = self._domain_service.hash_password(password)

                # 4. Create user aggregate
                user = UserAggregate.create(
                    user_id="user-123",
                    email=email,
                    password_hash=password_hash,
                    tenant_id="tenant-1",
                )

                return user
        ```
    """

    def __init__(
        self,
        password_hasher: PasswordHasher,
        email_validator: EmailValidator | None = None,
    ) -> None:
        """Initialize user domain service.

        Args:
            password_hasher: Service for hashing passwords.
            email_validator: Optional service for email validation.
        """
        self._password_hasher = password_hasher
        self._email_validator = email_validator

    def hash_password(self, password: str) -> str:
        """Hash a password using the configured hasher.

        Args:
            password: Plain text password.

        Returns:
            Hashed password.

        Example:
            ```python
            service = UserDomainService(password_hasher=Argon2PasswordHasher())
            hashed = service.hash_password("MySecurePassword123!")
            print(hashed)  # "$argon2id$v=19$m=65536,t=3,p=4$..."
            ```
        """
        return self._password_hasher.hash(password)

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against a hash.

        Args:
            password: Plain text password.
            hashed: Hashed password to verify against.

        Returns:
            True if password matches, False otherwise.

        Example:
            ```python
            service = UserDomainService(password_hasher=Argon2PasswordHasher())
            hashed = service.hash_password("MyPassword123!")

            # Correct password
            is_valid = service.verify_password("MyPassword123!", hashed)
            print(is_valid)  # True

            # Wrong password
            is_valid = service.verify_password("WrongPassword", hashed)
            print(is_valid)  # False
            ```
        """
        return self._password_hasher.verify(password, hashed)

    def validate_email(self, email: str) -> tuple[bool, str | None]:
        """Validate an email address.

        Args:
            email: Email address to validate.

        Returns:
            Tuple of (is_valid, error_message).

        Example:
            ```python
            service = UserDomainService(password_hasher=hasher)

            # Valid email
            is_valid, error = service.validate_email("user@example.com")
            print(is_valid, error)  # (True, None)

            # Invalid format
            is_valid, error = service.validate_email("not-an-email")
            print(is_valid, error)  # (False, "Invalid email format")

            # With custom validator that checks disposable emails
            validator = CustomEmailValidator()
            service = UserDomainService(hasher, email_validator=validator)

            is_valid, error = service.validate_email("user@tempmail.com")
            print(is_valid, error)  # (False, "Disposable email addresses are not allowed")
            ```
        """
        if not self._email_validator:
            # Basic validation only
            if _EMAIL_PATTERN.match(email):
                return True, None
            return False, "Invalid email format"

        if not self._email_validator.is_valid(email):
            return False, "Invalid email format"

        if self._email_validator.is_disposable(email):
            return False, "Disposable email addresses are not allowed"

        return True, None

    def validate_password_strength(self, password: str) -> tuple[bool, list[str]]:
        """Validate password strength.

        Checks for:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

        Args:
            password: Password to validate.

        Returns:
            Tuple of (is_valid, list of error messages).

        Example:
            ```python
            service = UserDomainService(password_hasher=hasher)

            # Weak password
            is_valid, errors = service.validate_password_strength("weak")
            print(is_valid)  # False
            print(errors)
            # ['Password must be at least 8 characters',
            #  'Password must contain at least one uppercase letter',
            #  'Password must contain at least one digit',
            #  'Password must contain at least one special character']

            # Strong password
            is_valid, errors = service.validate_password_strength("SecurePass123!")
            print(is_valid)  # True
            print(errors)  # []

            # Usage in validation
            password = request.password
            is_strong, errors = service.validate_password_strength(password)
            if not is_strong:
                raise ValidationError(f"Password validation failed: {', '.join(errors)}")
            ```
        """
        errors = []

        if len(password) < 8:
            errors.append("Password must be at least 8 characters")

        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")

        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")

        return len(errors) == 0, errors
