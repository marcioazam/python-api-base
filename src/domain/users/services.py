"""Domain services for the Users bounded context.

Domain services contain business logic that doesn't naturally fit
within a single entity or value object.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 2.5**
"""

from abc import ABC, abstractmethod
from typing import Protocol


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
        """
        return self._password_hasher.hash(password)

    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against a hash.
        
        Args:
            password: Plain text password.
            hashed: Hashed password to verify against.
            
        Returns:
            True if password matches, False otherwise.
        """
        return self._password_hasher.verify(password, hashed)
    
    def validate_email(self, email: str) -> tuple[bool, str | None]:
        """Validate an email address.
        
        Args:
            email: Email address to validate.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        if not self._email_validator:
            # Basic validation only
            import re
            pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if re.match(pattern, email):
                return True, None
            return False, "Invalid email format"
        
        if not self._email_validator.is_valid(email):
            return False, "Invalid email format"
        
        if self._email_validator.is_disposable(email):
            return False, "Disposable email addresses are not allowed"
        
        return True, None
    
    def validate_password_strength(self, password: str) -> tuple[bool, list[str]]:
        """Validate password strength.
        
        Args:
            password: Password to validate.
            
        Returns:
            Tuple of (is_valid, list of error messages).
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
