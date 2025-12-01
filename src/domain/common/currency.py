"""Currency and number formatting with locale support."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol
from enum import Enum


class RoundingMode(Enum):
    """Rounding modes for currency."""
    HALF_UP = "half_up"
    HALF_DOWN = "half_down"
    CEILING = "ceiling"
    FLOOR = "floor"


@dataclass
class Currency:
    """Currency definition."""
    code: str
    symbol: str
    name: str
    decimal_places: int = 2
    symbol_position: str = "before"


@dataclass
class Money:
    """Money value with currency."""
    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        if isinstance(self.amount, (int, float)):
            self.amount = Decimal(str(self.amount))

    def round(self, mode: RoundingMode = RoundingMode.HALF_UP) -> "Money":
        """Round to currency decimal places."""
        quantize = Decimal(10) ** -self.currency.decimal_places
        rounding = ROUND_HALF_UP
        return Money(
            amount=self.amount.quantize(quantize, rounding=rounding),
            currency=self.currency
        )

    def __add__(self, other: "Money") -> "Money":
        if self.currency.code != other.currency.code:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if self.currency.code != other.currency.code:
            raise ValueError("Cannot subtract different currencies")
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: Decimal | int | float) -> "Money":
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency.code == other.currency.code


# Common currencies
USD = Currency("USD", "$", "US Dollar", 2, "before")
EUR = Currency("EUR", "€", "Euro", 2, "before")
GBP = Currency("GBP", "£", "British Pound", 2, "before")
BRL = Currency("BRL", "R$", "Brazilian Real", 2, "before")
JPY = Currency("JPY", "¥", "Japanese Yen", 0, "before")


class ExchangeRateProvider(Protocol):
    """Protocol for exchange rate providers."""

    async def get_rate(self, from_currency: str, to_currency: str) -> Decimal: ...


@dataclass
class LocaleConfig:
    """Locale configuration for formatting."""
    decimal_separator: str = "."
    thousands_separator: str = ","
    currency_symbol_space: bool = False


class CurrencyFormatter:
    """Format currency values for display."""

    LOCALES: dict[str, LocaleConfig] = {
        "en_US": LocaleConfig(".", ",", False),
        "pt_BR": LocaleConfig(",", ".", True),
        "de_DE": LocaleConfig(",", ".", True),
        "fr_FR": LocaleConfig(",", " ", True),
    }

    def __init__(self, locale: str = "en_US") -> None:
        self._locale = self.LOCALES.get(locale, LocaleConfig())

    def format(self, money: Money) -> str:
        """Format money for display."""
        rounded = money.round()
        amount_str = self._format_number(
            rounded.amount,
            money.currency.decimal_places
        )

        if money.currency.symbol_position == "before":
            if self._locale.currency_symbol_space:
                return f"{money.currency.symbol} {amount_str}"
            return f"{money.currency.symbol}{amount_str}"
        else:
            if self._locale.currency_symbol_space:
                return f"{amount_str} {money.currency.symbol}"
            return f"{amount_str}{money.currency.symbol}"

    def _format_number(self, value: Decimal, decimal_places: int) -> str:
        """Format number with locale separators."""
        parts = str(value).split(".")
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else "0" * decimal_places

        # Add thousands separators
        formatted_int = ""
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                formatted_int = self._locale.thousands_separator + formatted_int
            formatted_int = digit + formatted_int

        if decimal_places > 0:
            decimal_part = decimal_part.ljust(decimal_places, "0")[:decimal_places]
            return f"{formatted_int}{self._locale.decimal_separator}{decimal_part}"
        return formatted_int


class CurrencyConverter:
    """Convert between currencies."""

    def __init__(self, rate_provider: ExchangeRateProvider) -> None:
        self._rate_provider = rate_provider
        self._currencies: dict[str, Currency] = {
            "USD": USD, "EUR": EUR, "GBP": GBP, "BRL": BRL, "JPY": JPY
        }

    def register_currency(self, currency: Currency) -> None:
        """Register a currency."""
        self._currencies[currency.code] = currency

    async def convert(
        self,
        money: Money,
        to_currency_code: str
    ) -> Money:
        """Convert money to another currency."""
        if money.currency.code == to_currency_code:
            return money

        rate = await self._rate_provider.get_rate(
            money.currency.code,
            to_currency_code
        )

        to_currency = self._currencies.get(to_currency_code)
        if not to_currency:
            raise ValueError(f"Unknown currency: {to_currency_code}")

        converted = Money(money.amount * rate, to_currency)
        return converted.round()


class InMemoryExchangeRateProvider:
    """In-memory exchange rate provider for testing."""

    def __init__(self) -> None:
        self._rates: dict[tuple[str, str], Decimal] = {
            ("USD", "EUR"): Decimal("0.92"),
            ("EUR", "USD"): Decimal("1.09"),
            ("USD", "BRL"): Decimal("4.97"),
            ("BRL", "USD"): Decimal("0.20"),
            ("USD", "GBP"): Decimal("0.79"),
            ("GBP", "USD"): Decimal("1.27"),
        }

    def set_rate(self, from_curr: str, to_curr: str, rate: Decimal) -> None:
        self._rates[(from_curr, to_curr)] = rate

    async def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        if from_currency == to_currency:
            return Decimal("1")
        rate = self._rates.get((from_currency, to_currency))
        if rate is None:
            raise ValueError(f"No rate for {from_currency} -> {to_currency}")
        return rate
