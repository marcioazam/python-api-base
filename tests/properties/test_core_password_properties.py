"""Property-based tests for password policy module.

**Feature: core-code-review**
**Validates: Requirements 7.1, 7.2, 7.3, 7.5**
"""

import string

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from my_app.core.auth.password_policy import (
    PasswordPolicy,
    PasswordValidator,
    PasswordValidationResult,
    COMMON_PASSWORDS,
)


class TestPasswordComplexityValidation:
    """Property tests for password complexity validation.
    
    **Feature: core-code-review, Property 11: Password Complexity Validation**
    **Validates: Requirements 7.1**
    """

    @given(st.text(min_size=1, max_size=11, alphabet=string.ascii_letters + string.digits))
    @settings(max_examples=100)
    def test_short_passwords_rejected(self, password: str):
        """Passwords shorter than min_length SHALL be rejected."""
        assume(len(password) < 12)
        
        validator = PasswordValidator()
        result = validator.validate(password)
        
        assert not result.valid
        assert any("12" in err or "length" in err.lower() for err in result.errors)

    @given(st.text(min_size=12, max_size=30, alphabet=string.ascii_lowercase))
    @settings(max_examples=50)
    def test_no_uppercase_rejected(self, password: str):
        """Passwords without uppercase SHALL be rejected when required."""
        assume(len(password) >= 12)
        assume(not any(c.isupper() for c in password))
        
        validator = PasswordValidator()
        result = validator.validate(password)
        
        assert not result.valid
        assert any("uppercase" in err.lower() for err in result.errors)

    @given(st.text(min_size=12, max_size=30, alphabet=string.ascii_uppercase))
    @settings(max_examples=50)
    def test_no_lowercase_rejected(self, password: str):
        """Passwords without lowercase SHALL be rejected when required."""
        assume(len(password) >= 12)
        assume(not any(c.islower() for c in password))
        
        validator = PasswordValidator()
        result = validator.validate(password)
        
        assert not result.valid
        assert any("lowercase" in err.lower() for err in result.errors)

    @given(st.text(min_size=12, max_size=30, alphabet=string.ascii_letters))
    @settings(max_examples=50)
    def test_no_digit_rejected(self, password: str):
        """Passwords without digits SHALL be rejected when required."""
        assume(len(password) >= 12)
        assume(not any(c.isdigit() for c in password))
        
        validator = PasswordValidator()
        result = validator.validate(password)
        
        assert not result.valid
        assert any("digit" in err.lower() for err in result.errors)


class TestCommonPasswordRejection:
    """Property tests for common password rejection.
    
    **Feature: core-code-review, Property 12: Common Password Rejection**
    **Validates: Requirements 7.2**
    """

    @given(st.sampled_from(list(COMMON_PASSWORDS)[:50]))
    @settings(max_examples=50)
    def test_common_passwords_rejected(self, password: str):
        """All passwords in COMMON_PASSWORDS SHALL be rejected."""
        validator = PasswordValidator()
        result = validator.validate(password)
        
        assert not result.valid
        assert any("common" in err.lower() for err in result.errors)

    def test_common_passwords_case_insensitive(self):
        """Common password check SHALL be case-insensitive."""
        validator = PasswordValidator()
        
        # Test uppercase version of common password
        result = validator.validate("PASSWORD")
        assert not result.valid
        assert any("common" in err.lower() for err in result.errors)


class TestPasswordStrengthScoreBounds:
    """Property tests for password strength score bounds.
    
    **Feature: core-code-review, Property 13: Password Strength Score Bounds**
    **Validates: Requirements 7.3**
    """

    @given(st.text(min_size=0, max_size=200))
    @settings(max_examples=100)
    def test_strength_score_in_valid_range(self, password: str):
        """For any password, strength_score SHALL be in [0, 100]."""
        validator = PasswordValidator()
        result = validator.validate(password)
        
        assert 0 <= result.strength_score <= 100

    def test_strong_password_high_score(self):
        """Strong passwords SHALL have high scores."""
        validator = PasswordValidator()
        
        # Password meeting all requirements
        strong_password = "MyStr0ng!Pass#2024"
        result = validator.validate(strong_password)
        
        assert result.valid
        assert result.strength_score >= 80


class TestArgon2idHashFormat:
    """Property tests for Argon2id hash format.
    
    **Feature: core-code-review, Property 14: Argon2id Hash Format**
    **Validates: Requirements 7.5**
    """

    def test_hash_uses_argon2id(self):
        """hash_password() SHALL produce Argon2id hash."""
        validator = PasswordValidator()
        
        # Valid password meeting all requirements
        password = "MyStr0ng!Pass#2024"
        hashed = validator.hash_password(password)
        
        assert hashed.startswith("$argon2id$")

    def test_hash_password_validates_first(self):
        """hash_password() SHALL validate password before hashing."""
        validator = PasswordValidator()
        
        # Invalid password (too short)
        with pytest.raises(ValueError) as exc_info:
            validator.hash_password("short")
        
        assert "policy" in str(exc_info.value).lower()

    def test_verify_password_works(self):
        """verify_password() SHALL correctly verify hashed passwords."""
        validator = PasswordValidator()
        
        password = "MyStr0ng!Pass#2024"
        hashed = validator.hash_password(password)
        
        assert validator.verify_password(password, hashed)
        assert not validator.verify_password("wrong_password", hashed)


class TestPasswordPolicyConfiguration:
    """Tests for password policy configuration."""

    def test_custom_policy_respected(self):
        """Custom policy settings SHALL be respected."""
        policy = PasswordPolicy(
            min_length=8,
            require_uppercase=False,
            require_special=False,
        )
        validator = PasswordValidator(policy=policy)
        
        # Password that would fail default policy but passes custom
        result = validator.validate("password123")
        
        # Should only fail on common password check
        assert not result.valid
        assert any("common" in err.lower() for err in result.errors)

    def test_get_requirements_returns_descriptions(self):
        """get_requirements() SHALL return human-readable descriptions."""
        validator = PasswordValidator()
        requirements = validator.get_requirements()
        
        assert isinstance(requirements, list)
        assert len(requirements) > 0
        assert all(isinstance(r, str) for r in requirements)
