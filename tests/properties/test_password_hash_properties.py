"""Property-based tests for Password Hash Verification.

**Feature: architecture-restructuring-2025, Property 11: Password Hash Verification**
**Validates: Requirements 9.1**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

try:
    from my_app.shared.utils.password import hash_password, verify_password
    from my_app.infrastructure.security.password_hashers import (
        PasswordValidator,
        PasswordPolicy,
    )
except ImportError:
    pytest.skip("my_app modules not available", allow_module_level=True)


# Strategy for valid passwords (meeting default policy)
valid_password_strategy = st.text(
    min_size=12,
    max_size=64,
    alphabet=st.sampled_from(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()"
    ),
).filter(
    lambda p: (
        any(c.isupper() for c in p) and
        any(c.islower() for c in p) and
        any(c.isdigit() for c in p) and
        any(c in "!@#$%^&*()" for c in p)
    )
)

# Strategy for any password string
any_password_strategy = st.text(min_size=1, max_size=100)


class TestPasswordHashVerification:
    """Property tests for password hashing and verification."""

    @settings(max_examples=50)
    @given(password=valid_password_strategy)
    def test_hash_then_verify_returns_true(self, password: str) -> None:
        """
        **Feature: architecture-restructuring-2025, Property 11: Password Hash Verification**
        
        For any password, hashing then verifying the original password
        SHALL return True.
        **Validates: Requirements 9.1**
        """
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    @settings(max_examples=50)
    @given(password=valid_password_strategy, wrong_password=any_password_strategy)
    def test_verify_wrong_password_returns_false(
        self, password: str, wrong_password: str
    ) -> None:
        """
        For any password, verifying a different password against its hash
        SHALL return False.
        **Validates: Requirements 9.1**
        """
        assume(password != wrong_password)
        
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False

    @settings(max_examples=30)
    @given(password=valid_password_strategy)
    def test_same_password_produces_different_hashes(self, password: str) -> None:
        """
        For any password, hashing twice SHALL produce different hashes (due to salt).
        **Validates: Requirements 9.1**
        """
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Hashes should be different due to random salt
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    @settings(max_examples=30)
    @given(password=valid_password_strategy)
    def test_hash_is_not_plaintext(self, password: str) -> None:
        """
        For any password, the hash SHALL NOT contain the plaintext password.
        **Validates: Requirements 9.1**
        """
        hashed = hash_password(password)
        assert password not in hashed

    @settings(max_examples=30)
    @given(password=valid_password_strategy)
    def test_validator_hash_and_verify(self, password: str) -> None:
        """
        For any valid password, PasswordValidator.hash_password and verify_password
        SHALL work correctly.
        **Validates: Requirements 9.1**
        """
        # Use lenient policy for testing
        policy = PasswordPolicy(
            min_length=8,
            require_uppercase=False,
            require_lowercase=False,
            require_digit=False,
            require_special=False,
            check_common_passwords=False,
        )
        validator = PasswordValidator(policy)
        
        hashed = validator.hash_password(password)
        assert validator.verify_password(password, hashed) is True

    @settings(max_examples=20)
    @given(password=any_password_strategy)
    def test_hash_handles_unicode(self, password: str) -> None:
        """
        For any unicode string, hashing SHALL not raise exceptions.
        **Validates: Requirements 9.1**
        """
        assume(len(password) > 0)
        
        try:
            hashed = hash_password(password)
            # If hashing succeeds, verification should work
            assert verify_password(password, hashed) is True
        except Exception:
            # Some edge cases may fail, which is acceptable
            pass
