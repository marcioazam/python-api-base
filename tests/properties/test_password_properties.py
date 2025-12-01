"""Property-based tests for password hashing.

**Feature: generic-fastapi-crud, Property 21: Password Hash Verification**
**Validates: Requirements 16.3**
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.shared.utils.password import hash_password, verify_password


# Strategy for generating valid passwords
password_strategy = st.text(
    min_size=1,
    max_size=72,  # Argon2 has practical limits
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        blacklist_characters="\x00",  # Null bytes can cause issues
    ),
)


class TestPasswordHashing:
    """Property tests for password hashing."""

    @settings(max_examples=10, deadline=None)
    @given(password=password_strategy)
    def test_hash_then_verify_succeeds(self, password: str) -> None:
        """
        **Feature: generic-fastapi-crud, Property 21: Password Hash Verification**

        For any password string, hashing followed by verification with the same
        password SHALL return True.
        """
        hashed = hash_password(password)
        assert verify_password(password, hashed), (
            f"Verification should succeed for password: {password!r}"
        )

    @settings(max_examples=10, deadline=None)
    @given(
        password1=password_strategy,
        password2=password_strategy,
    )
    def test_different_passwords_fail_verification(
        self, password1: str, password2: str
    ) -> None:
        """
        **Feature: generic-fastapi-crud, Property 21: Password Hash Verification**

        For any two different passwords, verification with a different password
        SHALL return False.
        """
        # Skip if passwords happen to be the same
        if password1 == password2:
            return

        hashed = hash_password(password1)
        assert not verify_password(password2, hashed), (
            "Verification should fail for different password"
        )

    @settings(max_examples=5, deadline=None)
    @given(password=password_strategy)
    def test_same_password_produces_different_hashes(self, password: str) -> None:
        """
        For any password, hashing twice SHALL produce different hash strings
        (due to random salt).
        """
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2, "Same password should produce different hashes"

    @settings(max_examples=5, deadline=None)
    @given(password=password_strategy)
    def test_hash_format_is_argon2(self, password: str) -> None:
        """
        For any password, the hash SHALL be in Argon2 format.
        """
        hashed = hash_password(password)
        assert hashed.startswith("$argon2"), f"Hash should be Argon2 format: {hashed}"

    def test_empty_password_raises_error(self) -> None:
        """Hashing an empty password SHALL raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            hash_password("")

    def test_verify_with_empty_password_returns_false(self) -> None:
        """Verifying with empty password SHALL return False."""
        hashed = hash_password("test")
        assert not verify_password("", hashed)

    def test_verify_with_empty_hash_returns_false(self) -> None:
        """Verifying with empty hash SHALL return False."""
        assert not verify_password("test", "")

    def test_verify_with_invalid_hash_returns_false(self) -> None:
        """Verifying with invalid hash format SHALL return False."""
        assert not verify_password("test", "invalid_hash")
        assert not verify_password("test", "$invalid$hash$format")
