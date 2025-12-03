"""Unit tests for common domain value objects.

**Feature: domain-value-objects-testing**
**Validates: Percentage, Slug, Money validation and operations**

Tests verify:
- Validation rules (range, format, pattern)
- Immutability (frozen=True)
- Factory methods
- Arithmetic operations (Money)
- String representation
- Edge cases and boundaries
"""

import pytest
from decimal import Decimal
from hypothesis import given, strategies as st

from src.domain.common.value_objects.value_objects import (
    Money,
    Percentage,
    Slug,
    CurrencyCode,
)


class TestPercentage:
    """Tests for Percentage value object."""

    def test_valid_percentages_accepted(self) -> None:
        """Test that valid percentages are accepted."""
        valid_values = [0, 0.0, 15.5, 50, 75.25, 99.99, 100, 100.0]

        for value in valid_values:
            percentage = Percentage(value=value)
            assert percentage.value == value

    def test_zero_percentage_accepted(self) -> None:
        """Test that 0% is valid."""
        percentage = Percentage(value=0)
        assert percentage.value == 0
        assert percentage.as_factor() == 0.0

    def test_hundred_percentage_accepted(self) -> None:
        """Test that 100% is valid."""
        percentage = Percentage(value=100)
        assert percentage.value == 100
        assert percentage.as_factor() == 1.0

    def test_negative_percentage_raises_error(self) -> None:
        """Test that negative percentages raise ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            Percentage(value=-1)

        with pytest.raises(ValueError, match="cannot be negative"):
            Percentage(value=-0.1)

        with pytest.raises(ValueError, match="cannot be negative"):
            Percentage(value=-100)

    def test_over_hundred_raises_error(self) -> None:
        """Test that percentages over 100 raise ValueError."""
        with pytest.raises(ValueError, match="cannot exceed 100"):
            Percentage(value=100.01)

        with pytest.raises(ValueError, match="cannot exceed 100"):
            Percentage(value=101)

        with pytest.raises(ValueError, match="cannot exceed 100"):
            Percentage(value=200)

    def test_as_factor_conversion(self) -> None:
        """Test conversion to decimal factor."""
        assert Percentage(value=0).as_factor() == 0.0
        assert Percentage(value=50).as_factor() == 0.5
        assert Percentage(value=100).as_factor() == 1.0
        assert Percentage(value=15.5).as_factor() == 0.155
        assert Percentage(value=75).as_factor() == 0.75

    def test_string_representation(self) -> None:
        """Test __str__ includes % symbol."""
        assert str(Percentage(value=15.5)) == "15.5%"
        assert str(Percentage(value=0)) == "0%"
        assert str(Percentage(value=100)) == "100%"

    def test_immutability(self) -> None:
        """Test that Percentage is immutable (frozen=True)."""
        percentage = Percentage(value=50)

        with pytest.raises(AttributeError):
            percentage.value = 75  # type: ignore

    def test_equality(self) -> None:
        """Test value object equality."""
        p1 = Percentage(value=50)
        p2 = Percentage(value=50)
        p3 = Percentage(value=75)

        assert p1 == p2
        assert p1 != p3
        assert hash(p1) == hash(p2)

    @given(st.floats(min_value=0.0, max_value=100.0))
    def test_property_valid_percentages_always_accepted(self, value: float) -> None:
        """Property test: valid percentages are always accepted."""
        percentage = Percentage(value=value)
        assert percentage.value == value
        assert 0.0 <= percentage.as_factor() <= 1.0


class TestSlug:
    """Tests for Slug value object."""

    def test_valid_slugs_accepted(self) -> None:
        """Test that valid slugs are accepted."""
        valid_slugs = [
            "hello",
            "hello-world",
            "test-slug-123",
            "a",
            "product-2024",
            "my-awesome-post",
            "123",
            "test1-test2-test3",
        ]

        for slug_str in valid_slugs:
            slug = Slug(value=slug_str)
            assert slug.value == slug_str
            assert str(slug) == slug_str

    def test_empty_slug_raises_error(self) -> None:
        """Test that empty slug raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Slug(value="")

    def test_uppercase_letters_raise_error(self) -> None:
        """Test that uppercase letters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid slug format"):
            Slug(value="Hello")

        with pytest.raises(ValueError, match="Invalid slug format"):
            Slug(value="hello-World")

    def test_invalid_characters_raise_error(self) -> None:
        """Test that invalid characters raise ValueError."""
        invalid_slugs = [
            "hello world",  # space
            "hello_world",  # underscore
            "hello.world",  # dot
            "hello@world",  # @
            "hello!",  # exclamation
            "hello#123",  # hash
            "hello$world",  # dollar
            "test%slug",  # percent
            "slug&name",  # ampersand
            "test*slug",  # asterisk
            "slug(test)",  # parentheses
            "test+slug",  # plus
            "slug=name",  # equals
            "test/slug",  # forward slash
            "slug\\name",  # backslash
        ]

        for invalid in invalid_slugs:
            with pytest.raises(ValueError, match="Invalid slug format"):
                Slug(value=invalid)

    def test_slug_starting_with_hyphen_raises_error(self) -> None:
        """Test that slug starting with hyphen raises ValueError."""
        with pytest.raises(ValueError, match="cannot start or end with hyphen"):
            Slug(value="-hello")

        with pytest.raises(ValueError, match="cannot start or end with hyphen"):
            Slug(value="-test-slug")

    def test_slug_ending_with_hyphen_raises_error(self) -> None:
        """Test that slug ending with hyphen raises ValueError."""
        with pytest.raises(ValueError, match="cannot start or end with hyphen"):
            Slug(value="hello-")

        with pytest.raises(ValueError, match="cannot start or end with hyphen"):
            Slug(value="test-slug-")

    def test_consecutive_hyphens_raise_error(self) -> None:
        """Test that consecutive hyphens raise ValueError."""
        with pytest.raises(ValueError, match="cannot contain consecutive hyphens"):
            Slug(value="hello--world")

        with pytest.raises(ValueError, match="cannot contain consecutive hyphens"):
            Slug(value="test---slug")

    def test_from_text_factory_method(self) -> None:
        """Test Slug.from_text() factory method."""
        # Basic conversion
        slug = Slug.from_text("Hello World")
        assert slug.value == "hello-world"

        # With punctuation
        slug = Slug.from_text("Hello, World!")
        assert slug.value == "hello-world"

        # With special characters
        slug = Slug.from_text("Product #123 @ Store")
        assert slug.value == "product-123-store"

        # Multiple spaces
        slug = Slug.from_text("Hello    World")
        assert slug.value == "hello-world"

        # Leading/trailing spaces
        slug = Slug.from_text("  Hello World  ")
        assert slug.value == "hello-world"

        # Already lowercase
        slug = Slug.from_text("already-lowercase")
        assert slug.value == "already-lowercase"

    def test_from_text_removes_accents_implicitly(self) -> None:
        """Test that from_text handles non-ASCII characters."""
        # Non-ASCII characters are removed
        slug = Slug.from_text("Café São Paulo")
        assert slug.value == "caf-s-o-paulo"

        slug = Slug.from_text("Résumé")
        assert slug.value == "r-sum"

    def test_from_text_handles_numbers(self) -> None:
        """Test that from_text preserves numbers."""
        slug = Slug.from_text("Product 123")
        assert slug.value == "product-123"

        slug = Slug.from_text("2024 Guide")
        assert slug.value == "2024-guide"

    def test_immutability(self) -> None:
        """Test that Slug is immutable (frozen=True)."""
        slug = Slug(value="hello-world")

        with pytest.raises(AttributeError):
            slug.value = "new-slug"  # type: ignore

    def test_equality(self) -> None:
        """Test value object equality."""
        slug1 = Slug(value="hello-world")
        slug2 = Slug(value="hello-world")
        slug3 = Slug(value="other-slug")

        assert slug1 == slug2
        assert slug1 != slug3
        assert hash(slug1) == hash(slug2)

    @given(
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
            min_size=1,
            max_size=100,
        ).filter(
            lambda s: not s.startswith("-")
            and not s.endswith("-")
            and "--" not in s
        )
    )
    def test_property_valid_slugs_always_accepted(self, slug_str: str) -> None:
        """Property test: valid slugs are always accepted."""
        slug = Slug(value=slug_str)
        assert slug.value == slug_str


class TestMoney:
    """Tests for Money value object."""

    def test_valid_money_accepted(self) -> None:
        """Test that valid money values are accepted."""
        money = Money(amount=Decimal("29.99"), currency="USD")
        assert money.amount == Decimal("29.99")
        assert money.currency == "USD"

    def test_money_from_float_converted_to_decimal(self) -> None:
        """Test that float amounts are converted to Decimal."""
        money = Money(amount=29.99, currency="USD")  # type: ignore
        assert isinstance(money.amount, Decimal)
        assert money.amount == Decimal("29.99")

    def test_money_rounded_to_two_decimals(self) -> None:
        """Test that amounts are rounded to 2 decimal places."""
        money = Money(amount=Decimal("29.999"), currency="USD")
        assert money.amount == Decimal("30.00")

        money = Money(amount=Decimal("29.994"), currency="USD")
        assert money.amount == Decimal("29.99")

    def test_addition_same_currency(self) -> None:
        """Test adding money with same currency."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("5.50"), currency="USD")
        result = m1 + m2

        assert result.amount == Decimal("15.50")
        assert result.currency == "USD"

    def test_addition_different_currency_raises_error(self) -> None:
        """Test that adding different currencies raises ValueError."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("5.00"), currency="EUR")

        with pytest.raises(ValueError, match="different currencies"):
            _ = m1 + m2

    def test_subtraction_same_currency(self) -> None:
        """Test subtracting money with same currency."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("3.50"), currency="USD")
        result = m1 - m2

        assert result.amount == Decimal("6.50")
        assert result.currency == "USD"

    def test_subtraction_different_currency_raises_error(self) -> None:
        """Test that subtracting different currencies raises ValueError."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("5.00"), currency="EUR")

        with pytest.raises(ValueError, match="different currencies"):
            _ = m1 - m2

    def test_multiplication_by_factor(self) -> None:
        """Test multiplying money by a factor."""
        money = Money(amount=Decimal("10.00"), currency="USD")

        result = money * 2
        assert result.amount == Decimal("20.00")

        result = money * 0.5
        assert result.amount == Decimal("5.00")

        result = money * Decimal("1.5")
        assert result.amount == Decimal("15.00")

    def test_negation(self) -> None:
        """Test negating money amount."""
        money = Money(amount=Decimal("10.00"), currency="USD")
        negated = -money

        assert negated.amount == Decimal("-10.00")
        assert negated.currency == "USD"

    def test_absolute_value(self) -> None:
        """Test absolute value of money."""
        money = Money(amount=Decimal("-10.00"), currency="USD")
        absolute = abs(money)

        assert absolute.amount == Decimal("10.00")
        assert absolute.currency == "USD"

    def test_boolean_conversion(self) -> None:
        """Test truthiness of money (non-zero amounts are True)."""
        assert bool(Money(amount=Decimal("10.00"), currency="USD")) is True
        assert bool(Money(amount=Decimal("0.00"), currency="USD")) is False
        assert bool(Money(amount=Decimal("-5.00"), currency="USD")) is True

    def test_comparison_same_currency(self) -> None:
        """Test comparison operators with same currency."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("5.00"), currency="USD")
        m3 = Money(amount=Decimal("10.00"), currency="USD")

        assert m1 > m2
        assert m2 < m1
        assert m1 >= m3
        assert m1 <= m3

    def test_comparison_different_currency_raises_error(self) -> None:
        """Test that comparing different currencies raises ValueError."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("10.00"), currency="EUR")

        with pytest.raises(ValueError, match="different currencies"):
            _ = m1 > m2

    def test_zero_factory_method(self) -> None:
        """Test Money.zero() factory method."""
        zero = Money.zero("USD")
        assert zero.amount == Decimal("0")
        assert zero.currency == "USD"

        zero_default = Money.zero()
        assert zero_default.currency == "USD"

    def test_from_cents_factory_method(self) -> None:
        """Test Money.from_cents() factory method."""
        money = Money.from_cents(2999, "USD")
        assert money.amount == Decimal("29.99")
        assert money.currency == "USD"

    def test_to_cents_conversion(self) -> None:
        """Test conversion to cents."""
        money = Money(amount=Decimal("29.99"), currency="USD")
        assert money.to_cents() == 2999

        money = Money(amount=Decimal("100.00"), currency="USD")
        assert money.to_cents() == 10000

    def test_format_with_default_symbol(self) -> None:
        """Test formatting with default currency symbol."""
        money = Money(amount=Decimal("1234.56"), currency="USD")
        assert money.format() == "$1,234.56"

        money_eur = Money(amount=Decimal("1234.56"), currency="EUR")
        assert money_eur.format() == "€1,234.56"

        money_gbp = Money(amount=Decimal("1234.56"), currency="GBP")
        assert money_gbp.format() == "£1,234.56"

    def test_format_with_custom_symbol(self) -> None:
        """Test formatting with custom symbol."""
        money = Money(amount=Decimal("29.99"), currency="USD")
        assert money.format(symbol="US$") == "US$29.99"

    def test_immutability(self) -> None:
        """Test that Money is immutable (frozen=True)."""
        money = Money(amount=Decimal("10.00"), currency="USD")

        with pytest.raises(AttributeError):
            money.amount = Decimal("20.00")  # type: ignore

        with pytest.raises(AttributeError):
            money.currency = "EUR"  # type: ignore

    def test_equality(self) -> None:
        """Test value object equality."""
        m1 = Money(amount=Decimal("10.00"), currency="USD")
        m2 = Money(amount=Decimal("10.00"), currency="USD")
        m3 = Money(amount=Decimal("5.00"), currency="USD")
        m4 = Money(amount=Decimal("10.00"), currency="EUR")

        assert m1 == m2
        assert m1 != m3
        assert m1 != m4  # Different currency
        assert hash(m1) == hash(m2)
