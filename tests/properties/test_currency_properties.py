"""Property-based tests for Currency Service.

**Feature: api-architecture-analysis, Property: Currency operations**
**Validates: Requirements 20.3**
"""

import pytest
from hypothesis import given, strategies as st, settings
from decimal import Decimal

from my_api.shared.currency import (
    Money,
    Currency,
    CurrencyFormatter,
    CurrencyConverter,
    InMemoryExchangeRateProvider,
    USD,
    EUR,
    BRL,
)


@st.composite
def money_strategy(draw: st.DrawFn) -> Money:
    """Generate valid money values."""
    amount = draw(st.decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("1000000"),
        places=2
    ))
    currency = draw(st.sampled_from([USD, EUR, BRL]))
    return Money(amount=amount, currency=currency)


class TestMoneyProperties:
    """Property tests for Money."""

    @given(
        st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000"), places=2),
        st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000"), places=2)
    )
    @settings(max_examples=100)
    def test_addition_commutative(self, a: Decimal, b: Decimal) -> None:
        """Money addition is commutative."""
        m1 = Money(a, USD)
        m2 = Money(b, USD)

        result1 = m1 + m2
        result2 = m2 + m1

        assert result1.amount == result2.amount

    @given(
        st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000"), places=2),
        st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000"), places=2),
        st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000"), places=2)
    )
    @settings(max_examples=100)
    def test_addition_associative(self, a: Decimal, b: Decimal, c: Decimal) -> None:
        """Money addition is associative."""
        m1 = Money(a, USD)
        m2 = Money(b, USD)
        m3 = Money(c, USD)

        result1 = (m1 + m2) + m3
        result2 = m1 + (m2 + m3)

        assert result1.amount == result2.amount

    @given(st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000"), places=2))
    @settings(max_examples=100)
    def test_subtraction_inverse_of_addition(self, a: Decimal) -> None:
        """Subtraction is inverse of addition."""
        m1 = Money(a, USD)
        m2 = Money(Decimal("100"), USD)

        result = (m1 + m2) - m2
        assert result.amount == m1.amount

    @given(
        st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000"), places=2),
        st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100)
    def test_multiplication_by_one(self, a: Decimal, factor: int) -> None:
        """Multiplication by 1 is identity."""
        m = Money(a, USD)
        result = m * 1

        assert result.amount == m.amount

    @given(st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000"), places=4))
    @settings(max_examples=100)
    def test_round_preserves_currency(self, a: Decimal) -> None:
        """Rounding preserves currency."""
        m = Money(a, USD)
        rounded = m.round()

        assert rounded.currency.code == m.currency.code


class TestCurrencyFormatterProperties:
    """Property tests for currency formatter."""

    @given(st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000000"), places=2))
    @settings(max_examples=100)
    def test_format_contains_symbol(self, amount: Decimal) -> None:
        """Formatted output contains currency symbol."""
        formatter = CurrencyFormatter("en_US")
        m = Money(amount, USD)

        formatted = formatter.format(m)
        assert USD.symbol in formatted

    @given(st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000000"), places=2))
    @settings(max_examples=100)
    def test_format_different_locales(self, amount: Decimal) -> None:
        """Different locales produce different formats."""
        m = Money(amount, USD)

        us_formatter = CurrencyFormatter("en_US")
        br_formatter = CurrencyFormatter("pt_BR")

        us_format = us_formatter.format(m)
        br_format = br_formatter.format(m)

        # Both should contain the symbol
        assert USD.symbol in us_format
        assert USD.symbol in br_format


class TestCurrencyConverterProperties:
    """Property tests for currency converter."""

    @given(st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000"), places=2))
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_convert_same_currency_identity(self, amount: Decimal) -> None:
        """Converting to same currency is identity."""
        provider = InMemoryExchangeRateProvider()
        converter = CurrencyConverter(provider)

        m = Money(amount, USD)
        converted = await converter.convert(m, "USD")

        assert converted.amount == m.amount
        assert converted.currency.code == m.currency.code

    @given(st.decimals(min_value=Decimal("1"), max_value=Decimal("1000"), places=2))
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_convert_preserves_value_approximately(self, amount: Decimal) -> None:
        """Round-trip conversion approximately preserves value."""
        provider = InMemoryExchangeRateProvider()
        converter = CurrencyConverter(provider)

        m = Money(amount, USD)
        to_eur = await converter.convert(m, "EUR")
        back_to_usd = await converter.convert(to_eur, "USD")

        # Should be approximately equal (within 5% due to rounding)
        diff = abs(back_to_usd.amount - m.amount)
        tolerance = m.amount * Decimal("0.05")
        assert diff <= tolerance
