"""Secure password hashing using Argon2."""

from passlib.context import CryptContext

# Configure Argon2 as the password hashing algorithm
# Argon2 is the winner of the Password Hashing Competition (PHC)
_pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=16384,  # 16 MB (reduced for faster tests)
    argon2__time_cost=2,  # 2 iterations
    argon2__parallelism=2,  # 2 parallel threads
)


def hash_password(password: str) -> str:
    """Hash a password using Argon2.

    Args:
        password: Plain text password to hash.

    Returns:
        str: Hashed password string.

    Raises:
        ValueError: If password is empty.
    """
    if not password:
        raise ValueError("Password cannot be empty")
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify.
        hashed_password: Previously hashed password.

    Returns:
        bool: True if password matches, False otherwise.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Check if a password hash needs to be rehashed.

    This is useful when upgrading hash parameters or algorithms.

    Args:
        hashed_password: Previously hashed password.

    Returns:
        bool: True if hash should be regenerated.
    """
    if not hashed_password:
        return True
    try:
        return _pwd_context.needs_update(hashed_password)
    except Exception:
        return True
