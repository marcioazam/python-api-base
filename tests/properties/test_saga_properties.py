"""Property-based tests for Saga Pattern.

**Feature: api-architecture-analysis, Property Tests for Task 3.5**
**Validates: Requirements 9.3**
"""

import pytest
from hypothesis import given, settings, strategies as st

from my_app.infrastructure.db.saga import (
    Saga,
    SagaBuilder,
    SagaContext,
    SagaOrchestrator,
    SagaResult,
    SagaStatus,
    SagaStep,
    StepStatus,
)


# =============================================================================
# Test Helpers
# =============================================================================


class StepTracker:
    """Tracks step executions for testing."""

    def __init__(self) -> None:
        self.executed: list[str] = []
        self.compensated: list[str] = []
        self.fail_at: str | None = None

    def reset(self) -> None:
        self.executed.clear()
        self.compensated.clear()
        self.fail_at = None


tracker = StepTracker()


async def make_step(name: str) -> "StepAction":
    """Create a step action that tracks execution."""

    async def action(ctx: SagaContext) -> None:
        if tracker.fail_at == name:
            raise ValueError(f"Step {name} failed")
        tracker.executed.append(name)
        ctx.set(f"{name}_done", True)

    return action


async def make_compensation(name: str) -> "CompensationAction":
    """Create a compensation action that tracks execution."""

    async def compensation(ctx: SagaContext) -> None:
        tracker.compensated.append(name)

    return compensation


# Type aliases
type StepAction = "Callable[[SagaContext], Awaitable[None]]"
type CompensationAction = "Callable[[SagaContext], Awaitable[None]]"


# =============================================================================
# Strategies
# =============================================================================


@st.composite
def step_names(draw: st.DrawFn) -> list[str]:
    """Generate a list of unique step names."""
    count = draw(st.integers(min_value=1, max_value=10))
    names = [f"step_{i}" for i in range(count)]
    return names


# =============================================================================
# Property Tests
# =============================================================================


class TestSagaContextProperties:
    """Property-based tests for SagaContext."""

    @given(st.text(min_size=1, max_size=50), st.integers())
    @settings(max_examples=100)
    def test_context_set_get_round_trip(self, key: str, value: int) -> None:
        """Property: set then get returns same value.

        **Feature: api-architecture-analysis, Property: Context round-trip**
        **Validates: Requirements 9.3**
        """
        ctx = SagaContext(saga_id="test")
        ctx.set(key, value)
        assert ctx.get(key) == value

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_context_has_returns_correct_value(self, key: str) -> None:
        """Property: has() returns correct boolean.

        **Feature: api-architecture-analysis, Property: Context has**
        **Validates: Requirements 9.3**
        """
        ctx = SagaContext(saga_id="test")

        assert not ctx.has(key)
        ctx.set(key, "value")
        assert ctx.has(key)

    @given(st.dictionaries(st.text(min_size=1, max_size=20), st.integers(), max_size=10))
    @settings(max_examples=100)
    def test_context_clear_removes_all_results(
        self, values: dict[str, int]
    ) -> None:
        """Property: clear_results removes all stored values.

        **Feature: api-architecture-analysis, Property: Context clear**
        **Validates: Requirements 9.3**
        """
        ctx = SagaContext(saga_id="test")

        for key, value in values.items():
            ctx.set(key, value)

        ctx.clear_results()

        for key in values:
            assert not ctx.has(key)


class TestSagaStepProperties:
    """Property-based tests for SagaStep."""

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_step_initial_status_is_pending(self, name: str) -> None:
        """Property: New step has PENDING status.

        **Feature: api-architecture-analysis, Property: Step initial status**
        **Validates: Requirements 9.3**
        """

        async def dummy(ctx: SagaContext) -> None:
            pass

        step = SagaStep(name=name, action=dummy)
        assert step.status == StepStatus.PENDING

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_step_reset_restores_initial_state(self, name: str) -> None:
        """Property: reset() restores step to initial state.

        **Feature: api-architecture-analysis, Property: Step reset**
        **Validates: Requirements 9.3**
        """

        async def dummy(ctx: SagaContext) -> None:
            pass

        step = SagaStep(name=name, action=dummy)
        step.status = StepStatus.COMPLETED
        step.error = ValueError("test")

        step.reset()

        assert step.status == StepStatus.PENDING
        assert step.error is None


@pytest.mark.asyncio
class TestSagaExecutionProperties:
    """Property-based tests for saga execution."""

    @given(step_names())
    @settings(max_examples=50)
    async def test_all_steps_execute_on_success(self, names: list[str]) -> None:
        """Property: All steps execute when no failures.

        **Feature: api-architecture-analysis, Property: Full execution**
        **Validates: Requirements 9.3**
        """
        tracker.reset()

        builder = SagaBuilder("test-saga")
        for name in names:

            async def action(ctx: SagaContext, n: str = name) -> None:
                tracker.executed.append(n)

            async def compensation(ctx: SagaContext, n: str = name) -> None:
                tracker.compensated.append(n)

            builder.step(name, action, compensation)

        saga = builder.build()
        result = await saga.execute()

        assert result.status == SagaStatus.COMPLETED
        assert tracker.executed == names
        assert tracker.compensated == []

    @given(step_names())
    @settings(max_examples=50)
    async def test_compensation_executes_in_reverse_order(
        self, names: list[str]
    ) -> None:
        """Property: Compensation executes in reverse order of completion.

        **Feature: api-architecture-analysis, Property: Reverse compensation**
        **Validates: Requirements 9.3**
        """
        if len(names) < 2:
            return  # Need at least 2 steps

        tracker.reset()
        fail_at_index = len(names) - 1  # Fail at last step

        builder = SagaBuilder("test-saga")
        for i, name in enumerate(names):

            async def action(ctx: SagaContext, n: str = name, idx: int = i) -> None:
                if idx == fail_at_index:
                    raise ValueError(f"Step {n} failed")
                tracker.executed.append(n)

            async def compensation(ctx: SagaContext, n: str = name) -> None:
                tracker.compensated.append(n)

            builder.step(name, action, compensation)

        saga = builder.build()
        result = await saga.execute()

        assert result.status == SagaStatus.COMPENSATED
        # Compensation should be in reverse order of executed steps
        expected_compensation = list(reversed(tracker.executed))
        assert tracker.compensated == expected_compensation

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    async def test_context_data_available_to_all_steps(
        self, num_steps: int
    ) -> None:
        """Property: Context data is available to all steps.

        **Feature: api-architecture-analysis, Property: Context sharing**
        **Validates: Requirements 9.3**
        """
        received_data: list[dict] = []

        builder = SagaBuilder("test-saga")
        for i in range(num_steps):

            async def action(ctx: SagaContext, idx: int = i) -> None:
                received_data.append(ctx.data.copy())
                ctx.set(f"step_{idx}", True)

            builder.step(f"step_{i}", action)

        saga = builder.build()
        initial_data = {"key": "value", "number": 42}
        await saga.execute(initial_data)

        # All steps should have received the initial data
        for data in received_data:
            assert data["key"] == "value"
            assert data["number"] == 42

    @given(st.integers(min_value=1, max_value=5))
    @settings(max_examples=50)
    async def test_step_results_propagate_through_context(
        self, num_steps: int
    ) -> None:
        """Property: Step results are available to subsequent steps.

        **Feature: api-architecture-analysis, Property: Result propagation**
        **Validates: Requirements 9.3**
        """
        builder = SagaBuilder("test-saga")

        for i in range(num_steps):

            async def action(ctx: SagaContext, idx: int = i) -> None:
                # Check previous step's result
                if idx > 0:
                    prev_result = ctx.get(f"result_{idx - 1}")
                    assert prev_result == idx - 1
                # Set this step's result
                ctx.set(f"result_{idx}", idx)

            builder.step(f"step_{i}", action)

        saga = builder.build()
        result = await saga.execute()

        assert result.status == SagaStatus.COMPLETED


@pytest.mark.asyncio
class TestSagaBuilderProperties:
    """Property-based tests for SagaBuilder."""

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    async def test_builder_creates_saga_with_correct_name(
        self, name: str
    ) -> None:
        """Property: Builder creates saga with specified name.

        **Feature: api-architecture-analysis, Property: Builder name**
        **Validates: Requirements 9.3**
        """

        async def dummy(ctx: SagaContext) -> None:
            pass

        saga = SagaBuilder(name).step("step1", dummy).build()
        assert saga.name == name

    @given(step_names())
    @settings(max_examples=50)
    async def test_builder_preserves_step_order(self, names: list[str]) -> None:
        """Property: Builder preserves step order.

        **Feature: api-architecture-analysis, Property: Step order**
        **Validates: Requirements 9.3**
        """

        async def dummy(ctx: SagaContext) -> None:
            pass

        builder = SagaBuilder("test")
        for name in names:
            builder.step(name, dummy)

        saga = builder.build()
        step_names_result = [s.name for s in saga.steps]

        assert step_names_result == names

    def test_builder_raises_on_empty_saga(self) -> None:
        """Property: Builder raises error for empty saga.

        **Feature: api-architecture-analysis, Property: Builder validation**
        **Validates: Requirements 9.3**
        """
        builder = SagaBuilder("empty")

        with pytest.raises(ValueError, match="at least one step"):
            builder.build()


@pytest.mark.asyncio
class TestSagaResultProperties:
    """Property-based tests for SagaResult."""

    @given(step_names())
    @settings(max_examples=50)
    async def test_result_is_success_on_completion(self, names: list[str]) -> None:
        """Property: is_success is True when status is COMPLETED.

        **Feature: api-architecture-analysis, Property: Result success**
        **Validates: Requirements 9.3**
        """

        async def dummy(ctx: SagaContext) -> None:
            pass

        builder = SagaBuilder("test")
        for name in names:
            builder.step(name, dummy)

        saga = builder.build()
        result = await saga.execute()

        assert result.is_success
        assert result.status == SagaStatus.COMPLETED

    @given(st.integers(min_value=2, max_value=5))
    @settings(max_examples=50)
    async def test_result_is_compensated_on_failure(self, num_steps: int) -> None:
        """Property: is_compensated is True after compensation.

        **Feature: api-architecture-analysis, Property: Result compensated**
        **Validates: Requirements 9.3**
        """
        builder = SagaBuilder("test")

        for i in range(num_steps):

            async def action(ctx: SagaContext, idx: int = i) -> None:
                if idx == num_steps - 1:
                    raise ValueError("Fail")

            async def compensation(ctx: SagaContext) -> None:
                pass

            builder.step(f"step_{i}", action, compensation)

        saga = builder.build()
        result = await saga.execute()

        assert result.is_compensated
        assert result.status == SagaStatus.COMPENSATED


@pytest.mark.asyncio
class TestSagaOrchestratorProperties:
    """Property-based tests for SagaOrchestrator."""

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    async def test_orchestrator_register_and_get(self, name: str) -> None:
        """Property: Registered saga can be retrieved.

        **Feature: api-architecture-analysis, Property: Orchestrator register**
        **Validates: Requirements 9.3**
        """

        async def dummy(ctx: SagaContext) -> None:
            pass

        orchestrator = SagaOrchestrator()
        saga = SagaBuilder(name).step("step1", dummy).build()

        orchestrator.register(saga)
        retrieved = orchestrator.get_saga(name)

        assert retrieved is saga

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    async def test_orchestrator_unregister_removes_saga(self, name: str) -> None:
        """Property: Unregistered saga is no longer retrievable.

        **Feature: api-architecture-analysis, Property: Orchestrator unregister**
        **Validates: Requirements 9.3**
        """

        async def dummy(ctx: SagaContext) -> None:
            pass

        orchestrator = SagaOrchestrator()
        saga = SagaBuilder(name).step("step1", dummy).build()

        orchestrator.register(saga)
        assert orchestrator.unregister(name)
        assert orchestrator.get_saga(name) is None

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    async def test_orchestrator_tracks_execution_history(
        self, num_executions: int
    ) -> None:
        """Property: Orchestrator tracks all executions in history.

        **Feature: api-architecture-analysis, Property: Orchestrator history**
        **Validates: Requirements 9.3**
        """

        async def dummy(ctx: SagaContext) -> None:
            pass

        orchestrator = SagaOrchestrator()
        saga = SagaBuilder("test").step("step1", dummy).build()
        orchestrator.register(saga)

        for _ in range(num_executions):
            await orchestrator.execute("test")

        history = orchestrator.get_history()
        assert len(history) == num_executions

    async def test_orchestrator_raises_on_unknown_saga(self) -> None:
        """Property: Orchestrator raises error for unknown saga.

        **Feature: api-architecture-analysis, Property: Orchestrator validation**
        **Validates: Requirements 9.3**
        """
        orchestrator = SagaOrchestrator()

        with pytest.raises(ValueError, match="not registered"):
            await orchestrator.execute("unknown")



# =============================================================================
# Compensation Property Tests (Post-Refactoring)
# =============================================================================


@pytest.mark.asyncio
class TestSagaCompensationProperties:
    """Property tests for saga compensation after refactoring.

    **Feature: code-review-refactoring, Property 3: Saga Compensation Completeness**
    **Validates: Requirements 3.5, 12.2**
    """

    @given(st.integers(min_value=2, max_value=5))
    @settings(max_examples=50)
    async def test_compensation_executes_in_reverse_order(
        self, num_steps: int
    ) -> None:
        """Property: Compensation executes in reverse order of completion.

        **Feature: code-review-refactoring, Property 3: Saga Compensation Completeness**
        **Validates: Requirements 3.5, 12.2**
        """
        tracker.reset()

        # Create steps
        steps = []
        for i in range(num_steps):
            name = f"step_{i}"

            async def make_action(n: str = name) -> None:
                async def action(ctx: SagaContext) -> None:
                    if tracker.fail_at == n:
                        raise ValueError(f"Step {n} failed")
                    tracker.executed.append(n)

                return action

            async def make_comp(n: str = name) -> None:
                async def comp(ctx: SagaContext) -> None:
                    tracker.compensated.append(n)

                return comp

            action = await make_action()
            comp = await make_comp()
            steps.append(SagaStep(name=name, action=action, compensation=comp))

        # Fail at last step
        tracker.fail_at = f"step_{num_steps - 1}"

        saga = Saga(name="test-saga", steps=steps)
        result = await saga.execute()

        # Verify compensation order is reverse of execution
        assert result.status == SagaStatus.COMPENSATED
        assert tracker.compensated == list(reversed(tracker.executed))

    @given(st.integers(min_value=1, max_value=5), st.integers(min_value=0, max_value=4))
    @settings(max_examples=50)
    async def test_only_completed_steps_are_compensated(
        self, num_steps: int, fail_at_index: int
    ) -> None:
        """Property: Only completed steps are compensated.

        **Feature: code-review-refactoring, Property 3: Saga Compensation Completeness**
        **Validates: Requirements 3.5, 12.2**
        """
        if fail_at_index >= num_steps:
            fail_at_index = num_steps - 1

        tracker.reset()

        steps = []
        for i in range(num_steps):
            name = f"step_{i}"

            async def make_action(n: str = name, idx: int = i) -> None:
                async def action(ctx: SagaContext) -> None:
                    if idx == fail_at_index:
                        raise ValueError(f"Step {n} failed")
                    tracker.executed.append(n)

                return action

            async def make_comp(n: str = name) -> None:
                async def comp(ctx: SagaContext) -> None:
                    tracker.compensated.append(n)

                return comp

            action = await make_action()
            comp = await make_comp()
            steps.append(SagaStep(name=name, action=action, compensation=comp))

        saga = Saga(name="test-saga", steps=steps)
        result = await saga.execute()

        # Verify only executed steps were compensated
        if fail_at_index > 0:
            assert result.status == SagaStatus.COMPENSATED
            assert set(tracker.compensated) == set(tracker.executed)
        else:
            # First step failed, nothing to compensate
            assert result.status == SagaStatus.COMPENSATED
            assert len(tracker.compensated) == 0

    @given(st.text(min_size=1, max_size=20))
    @settings(max_examples=50)
    async def test_successful_saga_no_compensation(self, saga_name: str) -> None:
        """Property: Successful saga has no compensation.

        **Feature: code-review-refactoring, Property 3: Saga Compensation Completeness**
        **Validates: Requirements 3.5, 12.2**
        """
        tracker.reset()

        async def success_action(ctx: SagaContext) -> None:
            tracker.executed.append("success")

        async def compensation(ctx: SagaContext) -> None:
            tracker.compensated.append("success")

        saga = (
            SagaBuilder(saga_name)
            .step("success", success_action, compensation)
            .build()
        )

        result = await saga.execute()

        assert result.is_success
        assert result.status == SagaStatus.COMPLETED
        assert len(tracker.compensated) == 0
        assert len(tracker.executed) == 1


@pytest.mark.asyncio
class TestSagaBackwardCompatibility:
    """Property tests for saga backward compatibility after refactoring.

    **Feature: code-review-refactoring, Property 1: Backward Compatibility**
    **Validates: Requirements 1.2, 1.4**
    """

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_all_saga_symbols_importable(self, _: str) -> None:
        """Property: All original saga symbols are importable.

        **Feature: code-review-refactoring, Property 1: Backward Compatibility**
        **Validates: Requirements 1.2, 1.4**
        """
        from my_app.infrastructure.db.saga import (
            CompensationAction,
            Saga,
            SagaBuilder,
            SagaContext,
            SagaOrchestrator,
            SagaResult,
            SagaStatus,
            SagaStep,
            StepAction,
            StepResult,
            StepStatus,
        )

        assert Saga is not None
        assert SagaBuilder is not None
        assert SagaContext is not None
        assert SagaOrchestrator is not None
        assert SagaResult is not None
        assert SagaStatus is not None
        assert SagaStep is not None
        assert StepResult is not None
        assert StepStatus is not None

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_saga_context_behavior_unchanged(self, key: str) -> None:
        """Property: SagaContext behavior unchanged after refactoring.

        **Feature: code-review-refactoring, Property 1: Backward Compatibility**
        **Validates: Requirements 1.2, 1.4**
        """
        from my_app.infrastructure.db.saga import SagaContext

        ctx = SagaContext(saga_id="test", data={"initial": "data"})

        assert ctx.saga_id == "test"
        assert ctx.data == {"initial": "data"}
        assert not ctx.has(key)

        ctx.set(key, "value")
        assert ctx.has(key)
        assert ctx.get(key) == "value"

        ctx.clear_results()
        assert not ctx.has(key)
