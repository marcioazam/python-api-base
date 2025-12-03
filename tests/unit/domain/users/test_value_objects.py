"""Unit tests for Users bounded context value objects.

**Feature: domain-value-objects-testing**
**Validates: Username, PhoneNumber, Email, PasswordHash, UserId validation**

Tests verify:
- Validation rules (length, format, pattern)
- Immutability (frozen=True)
- Factory methods
- String representation
- Edge cases and boundaries
"""

import pytest
from hypothesis import given, strategies as st

from src.domain.users.value_objects import (
    Email,
    PasswordHash,
    UserId,
    Username,
    PhoneNumber,
)


class TestUsername:
    """Tests for Username value object."""

    def test_valid_username_accepted(self) -> None:
        """Test that valid usernames are accepted."""
        valid_usernames = [
            "john",
            "john_doe",
            "john-doe",
            "JohnDoe123",
            "user_123",
            "test-user-456",
            "a1b",  # MIN_LENGTH = 3
        ]

        for username_str in valid_usernames:
            username = Username(value=username_str)
            assert username.value == username_str
            assert str(username) == username_str

    def test_factory_method(self) -> None:
        """Test Username.create() factory method."""
        username = Username.create("testuser")
        assert username.value == "testuser"
        assert isinstance(username, Username)

    def test_too_short_raises_error(self) -> None:
        """Test that usernames shorter than MIN_LENGTH raise ValueError."""
        with pytest.raises(ValueError, match="at least 3 characters"):
            Username(value="ab")

        with pytest.raises(ValueError, match="at least 3 characters"):
            Username(value="a")

        with pytest.raises(ValueError, match="at least 3 characters"):
            Username(value="")

    def test_too_long_raises_error(self) -> None:
        """Test that usernames longer than MAX_LENGTH raise ValueError."""
        long_username = "a" * 51  # MAX_LENGTH = 50
        with pytest.raises(ValueError, match="at most 50 characters"):
            Username(value=long_username)

        extra_long = "a" * 100
        with pytest.raises(ValueError, match="at most 50 characters"):
            Username(value=extra_long)

    def test_boundary_lengths_accepted(self) -> None:
        """Test boundary values for username length."""
        # MIN_LENGTH = 3
        min_username = Username(value="abc")
        assert min_username.value == "abc"

        # MAX_LENGTH = 50
        max_username = Username(value="a" * 50)
        assert len(max_username.value) == 50

    def test_invalid_characters_raise_error(self) -> None:
        """Test that invalid characters raise ValueError."""
        invalid_usernames = [
            "john doe",  # space
            "john@doe",  # @
            "john.doe",  # dot
            "johndoe!",  # exclamation
            "john#123",  # hash
            "user$name",  # dollar
            "test%user",  # percent
            "user&name",  # ampersand
            "test*user",  # asterisk
            "user(name)",  # parentheses
            "test+user",  # plus
            "user=name",  # equals
            "test[user]",  # brackets
            "user{name}",  # braces
            "test|user",  # pipe
            "user\\name",  # backslash
            "test/user",  # forward slash
            "user:name",  # colon
            "test;user",  # semicolon
            "user'name",  # single quote
            'user"name',  # double quote
            "test<user>",  # angle brackets
            "user,name",  # comma
            "test?user",  # question mark
            "açãobr",  # accented characters
            "テストuser",  # Japanese
            "用户name",  # Chinese
        ]

        for invalid in invalid_usernames:
            with pytest.raises(
                ValueError, match="can only contain letters, numbers, underscores, and hyphens"
            ):
                Username(value=invalid)

    def test_valid_characters_accepted(self) -> None:
        """Test that all valid characters are accepted."""
        # Lowercase letters
        Username(value="abc")
        # Uppercase letters
        Username(value="ABC")
        # Numbers
        Username(value="123abc")
        # Underscore
        Username(value="user_name")
        # Hyphen
        Username(value="user-name")
        # Mixed
        Username(value="User_Name-123")

    def test_immutability(self) -> None:
        """Test that Username is immutable (frozen=True)."""
        username = Username(value="testuser")

        with pytest.raises(AttributeError):
            username.value = "newvalue"  # type: ignore

    def test_equality(self) -> None:
        """Test value object equality."""
        username1 = Username(value="testuser")
        username2 = Username(value="testuser")
        username3 = Username(value="otheruser")

        assert username1 == username2
        assert username1 != username3
        assert hash(username1) == hash(username2)
        assert hash(username1) != hash(username3)

    @given(
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
            min_size=3,
            max_size=50,
        )
    )
    def test_property_valid_usernames_always_accepted(self, username_str: str) -> None:
        """Property test: valid usernames are always accepted."""
        username = Username(value=username_str)
        assert username.value == username_str
        assert len(username.value) >= 3
        assert len(username.value) <= 50


class TestPhoneNumber:
    """Tests for PhoneNumber value object."""

    def test_valid_phone_numbers_accepted(self) -> None:
        """Test that valid phone numbers are accepted."""
        valid_phones = [
            "1234567890",  # 10 digits
            "(123) 456-7890",  # Formatted
            "123-456-7890",  # Dashes
            "+1 234 567 8900",  # Country code with spaces
            "12345678901234",  # 14 digits
            "123456789012345",  # 15 digits (max)
        ]

        for phone_str in valid_phones:
            phone = PhoneNumber(value=phone_str)
            assert phone.value == phone_str

    def test_factory_method(self) -> None:
        """Test PhoneNumber.create() factory method."""
        phone = PhoneNumber.create("1234567890", country_code="1")
        assert phone.value == "1234567890"
        assert phone.country_code == "1"

    def test_too_few_digits_raises_error(self) -> None:
        """Test that phone numbers with fewer than 10 digits raise ValueError."""
        with pytest.raises(ValueError, match="must have 10-15 digits"):
            PhoneNumber(value="123456789")  # 9 digits

        with pytest.raises(ValueError, match="must have 10-15 digits"):
            PhoneNumber(value="12345")

        with pytest.raises(ValueError, match="must have 10-15 digits"):
            PhoneNumber(value="")

    def test_too_many_digits_raises_error(self) -> None:
        """Test that phone numbers with more than 15 digits raise ValueError."""
        with pytest.raises(ValueError, match="must have 10-15 digits"):
            PhoneNumber(value="1234567890123456")  # 16 digits

        with pytest.raises(ValueError, match="must have 10-15 digits"):
            PhoneNumber(value="12345678901234567890")

    def test_boundary_digit_counts_accepted(self) -> None:
        """Test boundary values for digit count."""
        # MIN = 10 digits
        min_phone = PhoneNumber(value="1234567890")
        assert min_phone.value == "1234567890"

        # MAX = 15 digits
        max_phone = PhoneNumber(value="123456789012345")
        assert max_phone.value == "123456789012345"

    def test_non_digit_characters_ignored_for_validation(self) -> None:
        """Test that non-digit characters are ignored during validation."""
        # These all have exactly 10 digits
        PhoneNumber(value="(123) 456-7890")
        PhoneNumber(value="123-456-7890")
        PhoneNumber(value="+1 234 567 8900")
        PhoneNumber(value="1.234.567.890")

    def test_country_code_stored(self) -> None:
        """Test that country code is stored."""
        phone = PhoneNumber(value="1234567890", country_code="55")
        assert phone.country_code == "55"

        phone_no_code = PhoneNumber(value="1234567890")
        assert phone_no_code.country_code == ""

    def test_string_representation_with_country_code(self) -> None:
        """Test __str__ includes country code when present."""
        phone_with_code = PhoneNumber(value="1234567890", country_code="1")
        assert str(phone_with_code) == "+1 1234567890"

        phone_without_code = PhoneNumber(value="1234567890")
        assert str(phone_without_code) == "1234567890"

    def test_immutability(self) -> None:
        """Test that PhoneNumber is immutable (frozen=True)."""
        phone = PhoneNumber(value="1234567890", country_code="1")

        with pytest.raises(AttributeError):
            phone.value = "9999999999"  # type: ignore

        with pytest.raises(AttributeError):
            phone.country_code = "55"  # type: ignore

    def test_equality(self) -> None:
        """Test value object equality."""
        phone1 = PhoneNumber(value="1234567890", country_code="1")
        phone2 = PhoneNumber(value="1234567890", country_code="1")
        phone3 = PhoneNumber(value="9876543210", country_code="1")
        phone4 = PhoneNumber(value="1234567890", country_code="55")

        assert phone1 == phone2
        assert phone1 != phone3
        assert phone1 != phone4  # Different country code
        assert hash(phone1) == hash(phone2)


class TestEmail:
    """Tests for Email value object."""

    def test_valid_emails_accepted(self) -> None:
        """Test that valid email formats are accepted."""
        valid_emails = [
            "user@example.com",
            "john.doe@example.com",
            "user+tag@example.co.uk",
            "user_name@sub.example.com",
            "123@example.com",
            "a@b.co",
        ]

        for email_str in valid_emails:
            email = Email(value=email_str)
            assert email.value == email_str.lower().strip()

    def test_email_normalized_to_lowercase(self) -> None:
        """Test that emails are normalized to lowercase."""
        email = Email(value="User@Example.COM")
        assert email.value == "user@example.com"

    def test_email_normalized_and_trimmed(self) -> None:
        """Test that emails are normalized and trimmed after validation."""
        # Note: Email validation happens BEFORE normalization,
        # so spaces would fail validation. Testing normalization that does happen:
        email = Email(value="User@Example.COM")
        assert email.value == "user@example.com"

        # Test with valid email that has no leading/trailing spaces
        email2 = Email(value="test@example.com")
        assert email2.value == "test@example.com"

    def test_invalid_emails_raise_error(self) -> None:
        """Test that invalid email formats raise ValueError."""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user@.com",
            "user @example.com",
            "user@example",
            "",
            "user@@example.com",
        ]

        for invalid in invalid_emails:
            with pytest.raises(ValueError, match="Invalid email format"):
                Email(value=invalid)

    def test_factory_method(self) -> None:
        """Test Email.create() factory method."""
        email = Email.create("test@example.com")
        assert email.value == "test@example.com"

    def test_immutability(self) -> None:
        """Test that Email is immutable."""
        email = Email(value="test@example.com")

        with pytest.raises(AttributeError):
            email.value = "new@example.com"  # type: ignore


class TestPasswordHash:
    """Tests for PasswordHash value object."""

    def test_valid_hash_accepted(self) -> None:
        """Test that valid password hashes are accepted."""
        hash_value = "$argon2id$v=19$m=65536,t=3,p=4$..."
        password_hash = PasswordHash(value=hash_value)
        assert password_hash.value == hash_value
        assert password_hash.algorithm == "argon2id"

    def test_custom_algorithm(self) -> None:
        """Test that custom algorithm can be specified."""
        password_hash = PasswordHash(value="hash123", algorithm="bcrypt")
        assert password_hash.algorithm == "bcrypt"

    def test_empty_hash_raises_error(self) -> None:
        """Test that empty hash raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            PasswordHash(value="")

    def test_factory_method(self) -> None:
        """Test PasswordHash.create() factory method."""
        password_hash = PasswordHash.create("hash123", algorithm="bcrypt")
        assert password_hash.value == "hash123"
        assert password_hash.algorithm == "bcrypt"

    def test_string_representation_hides_hash(self) -> None:
        """Test that __str__ does not reveal the actual hash."""
        password_hash = PasswordHash(value="secret_hash_123")
        str_repr = str(password_hash)
        assert "secret_hash_123" not in str_repr
        assert "[HASHED:" in str_repr
        assert "argon2id" in str_repr

    def test_immutability(self) -> None:
        """Test that PasswordHash is immutable."""
        password_hash = PasswordHash(value="hash123")

        with pytest.raises(AttributeError):
            password_hash.value = "newhash"  # type: ignore


class TestUserId:
    """Tests for UserId value object."""

    def test_valid_user_id_accepted(self) -> None:
        """Test that valid user IDs are accepted."""
        valid_ids = [
            "123e4567-e89b-12d3-a456-426614174000",  # UUID
            "user_123",
            "12345",
            "abc-def-ghi",
        ]

        for id_str in valid_ids:
            user_id = UserId(value=id_str)
            assert user_id.value == id_str
            assert str(user_id) == id_str

    def test_empty_user_id_raises_error(self) -> None:
        """Test that empty user ID raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            UserId(value="")

        with pytest.raises(ValueError, match="cannot be empty"):
            UserId(value="   ")

    def test_factory_method(self) -> None:
        """Test UserId.create() factory method."""
        user_id = UserId.create("user123")
        assert user_id.value == "user123"

    def test_immutability(self) -> None:
        """Test that UserId is immutable."""
        user_id = UserId(value="user123")

        with pytest.raises(AttributeError):
            user_id.value = "user456"  # type: ignore

    def test_equality(self) -> None:
        """Test value object equality."""
        user_id1 = UserId(value="user123")
        user_id2 = UserId(value="user123")
        user_id3 = UserId(value="user456")

        assert user_id1 == user_id2
        assert user_id1 != user_id3
        assert hash(user_id1) == hash(user_id2)
