"""Generic Strategy pattern implementation.

Provides type-safe strategy pattern with runtime strategy selection.
Uses PEP 695 type parameter syntax.
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypeVar

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


class Strategy[TInput, TOutput](Protocol):
    """Protocol for strategy implementations.

    Type Parameters:
        TInput: Input type for the strategy.
        TOutput: Output type from the strategy.
    """

    async def execute(self, input_data: TInput) -> TOutput:
        """Execute the strategy.

        Args:
            input_data: Input data for the strategy.

        Returns:
            Result of applying the strategy.
        """
        ...


class SyncStrategy[TInput, TOutput](Protocol):
    """Protocol for synchronous strategy implementations."""

    def execute(self, input_data: TInput) -> TOutput:
        """Execute the strategy synchronously."""
        ...


class StrategyContext[TInput, TOutput]:
    """Context for executing strategies.

    Allows runtime selection and switching of strategies.

    Type Parameters:
        TInput: Input type for strategies.
        TOutput: Output type from strategies.

    Example:
        >>> context = StrategyContext[Order, float]()
        >>> context.set_strategy(StandardPricingStrategy())
        >>> price = await context.execute(order)
        >>> context.set_strategy(DiscountPricingStrategy(0.1))
        >>> discounted_price = await context.execute(order)
    """

    def __init__(self, strategy: Strategy[TInput, TOutput] | None = None) -> None:
        """Initialize context with optional strategy.

        Args:
            strategy: Initial strategy to use.
        """
        self._strategy = strategy

    def set_strategy(self, strategy: Strategy[TInput, TOutput]) -> None:
        """Set the current strategy.

        Args:
            strategy: Strategy to use.
        """
        self._strategy = strategy

    async def execute(self, input_data: TInput) -> TOutput:
        """Execute the current strategy.

        Args:
            input_data: Input data for the strategy.

        Returns:
            Result of applying the strategy.

        Raises:
            ValueError: If no strategy is set.
        """
        if self._strategy is None:
            raise ValueError("No strategy set")
        return await self._strategy.execute(input_data)

    @property
    def has_strategy(self) -> bool:
        """Check if a strategy is set."""
        return self._strategy is not None


class StrategyRegistry[TKey, TInput, TOutput]:
    """Registry for named strategies with runtime selection.

    Type Parameters:
        TKey: Key type for identifying strategies.
        TInput: Input type for strategies.
        TOutput: Output type from strategies.

    Example:
        >>> registry = StrategyRegistry[str, Payment, Receipt]()
        >>> registry.register("credit_card", CreditCardStrategy())
        >>> registry.register("paypal", PayPalStrategy())
        >>> receipt = await registry.execute("credit_card", payment)
    """

    def __init__(self) -> None:
        self._strategies: dict[TKey, Strategy[TInput, TOutput]] = {}
        self._default_key: TKey | None = None

    def register(
        self,
        key: TKey,
        strategy: Strategy[TInput, TOutput],
        is_default: bool = False,
    ) -> None:
        """Register a strategy.

        Args:
            key: Key to identify the strategy.
            strategy: Strategy implementation.
            is_default: Whether this is the default strategy.
        """
        self._strategies[key] = strategy
        if is_default:
            self._default_key = key

    def unregister(self, key: TKey) -> None:
        """Unregister a strategy."""
        self._strategies.pop(key, None)
        if self._default_key == key:
            self._default_key = None

    def get(self, key: TKey) -> Strategy[TInput, TOutput] | None:
        """Get a strategy by key."""
        return self._strategies.get(key)

    async def execute(
        self,
        key: TKey | None,
        input_data: TInput,
    ) -> TOutput:
        """Execute a strategy by key.

        Args:
            key: Key of strategy to execute (uses default if None).
            input_data: Input data for the strategy.

        Returns:
            Result of applying the strategy.

        Raises:
            KeyError: If strategy not found.
        """
        actual_key = key if key is not None else self._default_key
        if actual_key is None:
            raise KeyError("No strategy key provided and no default set")

        strategy = self._strategies.get(actual_key)
        if strategy is None:
            raise KeyError(f"No strategy registered for key: {actual_key}")

        return await strategy.execute(input_data)

    @property
    def registered_keys(self) -> list[TKey]:
        """Get list of registered strategy keys."""
        return list(self._strategies.keys())


class FunctionStrategy[TInput, TOutput]:
    """Strategy wrapping an async function.

    Example:
        >>> strategy = FunctionStrategy(calculate_discount)
        >>> result = await strategy.execute(order)
    """

    def __init__(self, func: Callable[[TInput], Awaitable[TOutput]]) -> None:
        """Initialize with async function.

        Args:
            func: Async function implementing the strategy.
        """
        self._func = func

    async def execute(self, input_data: TInput) -> TOutput:
        """Execute the wrapped function."""
        return await self._func(input_data)


class CompositeStrategy[TInput, TOutput]:
    """Strategy that combines multiple strategies.

    Executes all strategies and combines results using a reducer.

    Example:
        >>> composite = CompositeStrategy[Order, float](
        ...     strategies=[base_price, tax, shipping],
        ...     reducer=sum,
        ... )
        >>> total = await composite.execute(order)
    """

    def __init__(
        self,
        strategies: list[Strategy[TInput, TOutput]],
        reducer: Callable[[list[TOutput]], TOutput],
    ) -> None:
        """Initialize composite strategy.

        Args:
            strategies: List of strategies to execute.
            reducer: Function to combine results.
        """
        self._strategies = strategies
        self._reducer = reducer

    async def execute(self, input_data: TInput) -> TOutput:
        """Execute all strategies and combine results."""
        results = []
        for strategy in self._strategies:
            result = await strategy.execute(input_data)
            results.append(result)
        return self._reducer(results)

    def add_strategy(self, strategy: Strategy[TInput, TOutput]) -> None:
        """Add a strategy to the composite."""
        self._strategies.append(strategy)


def strategy[TInput, TOutput](
    func: Callable[[TInput], Awaitable[TOutput]]
) -> Strategy[TInput, TOutput]:
    """Decorator to create a strategy from an async function.

    Args:
        func: Async function to wrap.

    Returns:
        Strategy wrapping the function.

    Example:
        >>> @strategy
        ... async def premium_pricing(order: Order) -> float:
        ...     return order.subtotal * 0.9
    """
    return FunctionStrategy(func)
