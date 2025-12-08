"""Tests for Saga builder module.

Tests for SagaBuilder fluent API.
"""

import pytest

from infrastructure.db.saga.builder import SagaBuilder
from infrastructure.db.saga.context import SagaContext
from infrastructure.db.saga.orchestrator import SagaResult


class TestSagaBuilder:
    """Tests for SagaBuilder class."""

    def test_init_with_name(self) -> None:
        """Builder should store saga name."""
        builder = SagaBuilder("test-saga")
        assert builder._name == "test-saga"

    def test_init_empty_steps(self) -> None:
        """Builder should start with empty steps."""
        builder = SagaBuilder("test")
        assert builder._steps == []

    def test_init_no_callbacks(self) -> None:
        """Builder should start with no callbacks."""
        builder = SagaBuilder("test")
        assert builder._on_complete is None
        assert builder._on_compensate is None
        assert builder._on_failure is None

    def test_step_adds_step(self) -> None:
        """step() should add a step to the builder."""

        async def action(ctx: SagaContext) -> None:
            pass

        builder = SagaBuilder("test")
        result = builder.step("step1", action)
        assert len(builder._steps) == 1
        assert builder._steps[0].name == "step1"
        assert result is builder  # Returns self for chaining

    def test_step_with_compensation(self) -> None:
        """step() should accept compensation function."""

        async def action(ctx: SagaContext) -> None:
            pass

        async def compensate(ctx: SagaContext) -> None:
            pass

        builder = SagaBuilder("test")
        builder.step("step1", action, compensate)
        assert builder._steps[0].compensation is compensate

    def test_step_without_compensation(self) -> None:
        """step() should work without compensation."""

        async def action(ctx: SagaContext) -> None:
            pass

        builder = SagaBuilder("test")
        builder.step("step1", action)
        assert builder._steps[0].compensation is None

    def test_multiple_steps(self) -> None:
        """Builder should support multiple steps."""

        async def action1(ctx: SagaContext) -> None:
            pass

        async def action2(ctx: SagaContext) -> None:
            pass

        async def action3(ctx: SagaContext) -> None:
            pass

        builder = SagaBuilder("test")
        builder.step("step1", action1).step("step2", action2).step("step3", action3)
        assert len(builder._steps) == 3
        assert builder._steps[0].name == "step1"
        assert builder._steps[1].name == "step2"
        assert builder._steps[2].name == "step3"

    def test_on_complete_sets_callback(self) -> None:
        """on_complete() should set completion callback."""

        async def callback(result: SagaResult) -> None:
            pass

        builder = SagaBuilder("test")
        result = builder.on_complete(callback)
        assert builder._on_complete is callback
        assert result is builder  # Returns self for chaining

    def test_on_compensate_sets_callback(self) -> None:
        """on_compensate() should set compensation callback."""

        async def callback(result: SagaResult) -> None:
            pass

        builder = SagaBuilder("test")
        result = builder.on_compensate(callback)
        assert builder._on_compensate is callback
        assert result is builder

    def test_on_failure_sets_callback(self) -> None:
        """on_failure() should set failure callback."""

        async def callback(result: SagaResult) -> None:
            pass

        builder = SagaBuilder("test")
        result = builder.on_failure(callback)
        assert builder._on_failure is callback
        assert result is builder

    def test_build_creates_saga(self) -> None:
        """build() should create a Saga instance."""

        async def action(ctx: SagaContext) -> None:
            pass

        builder = SagaBuilder("test-saga")
        builder.step("step1", action)
        saga = builder.build()
        assert saga.name == "test-saga"
        assert len(saga.steps) == 1

    def test_build_with_callbacks(self) -> None:
        """build() should include callbacks in saga."""

        async def action(ctx: SagaContext) -> None:
            pass

        async def on_complete(result: SagaResult) -> None:
            pass

        async def on_compensate(result: SagaResult) -> None:
            pass

        async def on_failure(result: SagaResult) -> None:
            pass

        builder = SagaBuilder("test")
        builder.step("step1", action)
        builder.on_complete(on_complete)
        builder.on_compensate(on_compensate)
        builder.on_failure(on_failure)
        saga = builder.build()
        # Saga uses private attributes for callbacks
        assert saga._on_complete is on_complete
        assert saga._on_compensate is on_compensate
        assert saga._on_failure is on_failure

    def test_build_raises_without_steps(self) -> None:
        """build() should raise ValueError if no steps."""
        builder = SagaBuilder("test")
        with pytest.raises(ValueError, match="at least one step"):
            builder.build()

    def test_fluent_api_chain(self) -> None:
        """Builder should support full fluent API chain."""

        async def action1(ctx: SagaContext) -> None:
            pass

        async def action2(ctx: SagaContext) -> None:
            pass

        async def comp1(ctx: SagaContext) -> None:
            pass

        async def on_complete(result: SagaResult) -> None:
            pass

        async def on_failure(result: SagaResult) -> None:
            pass

        saga = (
            SagaBuilder("order-saga")
            .step("create-order", action1, comp1)
            .step("process-payment", action2)
            .on_complete(on_complete)
            .on_failure(on_failure)
            .build()
        )
        assert saga.name == "order-saga"
        assert len(saga.steps) == 2
        # Saga uses private attributes for callbacks
        assert saga._on_complete is on_complete
        assert saga._on_failure is on_failure

    def test_step_preserves_action(self) -> None:
        """step() should preserve the action function."""

        async def my_action(ctx: SagaContext) -> None:
            ctx.set("key", "value")

        builder = SagaBuilder("test")
        builder.step("step1", my_action)
        assert builder._steps[0].action is my_action
