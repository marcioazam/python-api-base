"""Pipeline pattern with variadic generics (PEP 646).

Provides a type-safe pipeline for composing operations.
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, TypeVarTuple

T = TypeVar("T")
U = TypeVar("U")
Ts = TypeVarTuple("Ts")


class PipelineStep[TInput, TOutput](ABC):
    """Abstract base class for pipeline steps.

    Type Parameters:
        TInput: Input type for this step.
        TOutput: Output type from this step.
    """

    @abstractmethod
    async def execute(self, input_data: TInput) -> TOutput:
        """Execute this pipeline step.

        Args:
            input_data: Input data for this step.

        Returns:
            Transformed output data.
        """
        ...

    def __rshift__[TNext](
        self, next_step: "PipelineStep[TOutput, TNext]"
    ) -> "ChainedStep[TInput, TOutput, TNext]":
        """Chain this step with another using >> operator."""
        return ChainedStep(self, next_step)


class ChainedStep[TInput, TMiddle, TOutput](PipelineStep[TInput, TOutput]):
    """Two pipeline steps chained together."""

    def __init__(
        self,
        first: PipelineStep[TInput, TMiddle],
        second: PipelineStep[TMiddle, TOutput],
    ) -> None:
        self._first = first
        self._second = second

    async def execute(self, input_data: TInput) -> TOutput:
        """Execute both steps in sequence."""
        middle = await self._first.execute(input_data)
        return await self._second.execute(middle)


class FunctionStep[TInput, TOutput](PipelineStep[TInput, TOutput]):
    """Pipeline step wrapping an async function."""

    def __init__(self, func: Callable[[TInput], Awaitable[TOutput]]) -> None:
        self._func = func

    async def execute(self, input_data: TInput) -> TOutput:
        """Execute the wrapped function."""
        return await self._func(input_data)


class SyncFunctionStep[TInput, TOutput](PipelineStep[TInput, TOutput]):
    """Pipeline step wrapping a sync function."""

    def __init__(self, func: Callable[[TInput], TOutput]) -> None:
        self._func = func

    async def execute(self, input_data: TInput) -> TOutput:
        """Execute the wrapped sync function."""
        return self._func(input_data)


class Pipeline[TInput, TOutput]:
    """Generic pipeline for composing operations.

    Type Parameters:
        TInput: Input type for the pipeline.
        TOutput: Output type from the pipeline.

    Example:
        >>> pipeline = Pipeline[str, int]()
        >>> pipeline.add_step(parse_step)
        >>> pipeline.add_step(validate_step)
        >>> pipeline.add_step(transform_step)
        >>> result = await pipeline.execute("input")
    """

    def __init__(self) -> None:
        self._steps: list[PipelineStep[Any, Any]] = []

    def add_step[TStepOutput](
        self, step: PipelineStep[Any, TStepOutput]
    ) -> "Pipeline[TInput, TStepOutput]":
        """Add a step to the pipeline.

        Args:
            step: Pipeline step to add.

        Returns:
            Self for method chaining.
        """
        self._steps.append(step)
        return self  # type: ignore

    def add_function[TStepOutput](
        self, func: Callable[[Any], Awaitable[TStepOutput]]
    ) -> "Pipeline[TInput, TStepOutput]":
        """Add an async function as a pipeline step.

        Args:
            func: Async function to add.

        Returns:
            Self for method chaining.
        """
        self._steps.append(FunctionStep(func))
        return self  # type: ignore

    def add_sync_function[TStepOutput](
        self, func: Callable[[Any], TStepOutput]
    ) -> "Pipeline[TInput, TStepOutput]":
        """Add a sync function as a pipeline step.

        Args:
            func: Sync function to add.

        Returns:
            Self for method chaining.
        """
        self._steps.append(SyncFunctionStep(func))
        return self  # type: ignore

    async def execute(self, input_data: TInput) -> TOutput:
        """Execute all pipeline steps in sequence.

        Args:
            input_data: Initial input data.

        Returns:
            Final output after all steps.
        """
        result: Any = input_data
        for step in self._steps:
            result = await step.execute(result)
        return result

    def __len__(self) -> int:
        """Return number of steps in pipeline."""
        return len(self._steps)


def step[TInput, TOutput](
    func: Callable[[TInput], Awaitable[TOutput]]
) -> PipelineStep[TInput, TOutput]:
    """Create a pipeline step from an async function.

    Args:
        func: Async function to wrap.

    Returns:
        PipelineStep wrapping the function.

    Example:
        >>> @step
        ... async def parse(data: str) -> dict:
        ...     return json.loads(data)
    """
    return FunctionStep(func)


def sync_step[TInput, TOutput](
    func: Callable[[TInput], TOutput]
) -> PipelineStep[TInput, TOutput]:
    """Create a pipeline step from a sync function.

    Args:
        func: Sync function to wrap.

    Returns:
        PipelineStep wrapping the function.
    """
    return SyncFunctionStep(func)


# Convenience function for creating pipelines
def pipeline[TInput, TOutput]() -> Pipeline[TInput, TOutput]:
    """Create a new empty pipeline.

    Returns:
        New Pipeline instance.
    """
    return Pipeline[TInput, TOutput]()
