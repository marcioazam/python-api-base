"""Property-based tests for core container module.

**Feature: core-code-review**
**Validates: Requirements 3.4, 3.5, 11.5**
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from my_api.core.container import LifecycleManager, LifecycleHookError


class TestLifecycleHookExecutionOrder:
    """Property tests for lifecycle hook execution order.
    
    **Feature: core-code-review, Property 4: Lifecycle Hook Execution Order**
    **Validates: Requirements 3.4**
    """

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_startup_hooks_execute_in_registration_order(self, num_hooks: int):
        """For any sequence of hooks, run_startup() SHALL execute in registration order."""
        manager = LifecycleManager()
        execution_order: list[int] = []
        
        # Register hooks
        for i in range(num_hooks):
            def hook(idx=i):
                execution_order.append(idx)
            hook.__name__ = f"hook_{i}"
            manager.on_startup(hook)
        
        # Execute
        manager.run_startup()
        
        # Verify order
        assert execution_order == list(range(num_hooks))

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_shutdown_hooks_execute_in_reverse_order(self, num_hooks: int):
        """For any sequence of hooks, run_shutdown() SHALL execute in reverse order."""
        manager = LifecycleManager()
        execution_order: list[int] = []
        
        # Register hooks
        for i in range(num_hooks):
            def hook(idx=i):
                execution_order.append(idx)
            hook.__name__ = f"hook_{i}"
            manager.on_shutdown(hook)
        
        # Execute
        try:
            manager.run_shutdown()
        except LifecycleHookError:
            pass  # Ignore errors for this test
        
        # Verify reverse order
        assert execution_order == list(reversed(range(num_hooks)))


class TestLifecycleHookErrorAggregation:
    """Property tests for lifecycle hook error aggregation.
    
    **Feature: core-code-review, Property 5: Lifecycle Hook Error Aggregation**
    **Validates: Requirements 3.5**
    """

    @given(
        num_hooks=st.integers(min_value=3, max_value=10),
        failing_indices=st.lists(st.integers(min_value=0, max_value=9), min_size=1, max_size=5, unique=True),
    )
    @settings(max_examples=50)
    def test_all_shutdown_hooks_attempted_even_if_some_fail(
        self, num_hooks: int, failing_indices: list[int]
    ):
        """For any set of hooks where some fail, all SHALL be attempted."""
        # Adjust failing indices to be within range
        failing_indices = [i % num_hooks for i in failing_indices]
        
        manager = LifecycleManager()
        executed_hooks: list[int] = []
        
        # Register hooks
        for i in range(num_hooks):
            def hook(idx=i, should_fail=(i in failing_indices)):
                executed_hooks.append(idx)
                if should_fail:
                    raise RuntimeError(f"Hook {idx} failed")
            hook.__name__ = f"hook_{i}"
            manager.on_shutdown(hook)
        
        # Execute - should raise aggregated error
        with pytest.raises(LifecycleHookError) as exc_info:
            manager.run_shutdown()
        
        # All hooks should have been attempted
        assert len(executed_hooks) == num_hooks
        
        # Error should contain all failures
        assert len(exc_info.value.errors) == len(set(failing_indices))

    def test_no_error_when_all_hooks_succeed(self):
        """When all hooks succeed, no error SHALL be raised."""
        manager = LifecycleManager()
        
        def hook1():
            pass
        hook1.__name__ = "hook1"
        
        def hook2():
            pass
        hook2.__name__ = "hook2"
        
        manager.on_shutdown(hook1)
        manager.on_shutdown(hook2)
        
        # Should not raise
        manager.run_shutdown()


class TestLifecycleHookInspection:
    """Property tests for lifecycle hook inspection.
    
    **Feature: core-code-review**
    **Validates: Requirements 11.5**
    """

    @given(st.integers(min_value=0, max_value=10))
    @settings(max_examples=50)
    def test_get_hooks_returns_all_registered(self, num_hooks: int):
        """get_hooks() SHALL return all registered hooks."""
        manager = LifecycleManager()
        
        for i in range(num_hooks):
            def hook():
                pass
            hook.__name__ = f"startup_{i}"
            manager.on_startup(hook)
            
            def shutdown_hook():
                pass
            shutdown_hook.__name__ = f"shutdown_{i}"
            manager.on_shutdown(shutdown_hook)
        
        hooks = manager.get_hooks()
        
        assert len(hooks["startup"]) == num_hooks
        assert len(hooks["shutdown"]) == num_hooks

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_clear_hooks_removes_all(self, num_hooks: int):
        """clear_hooks() SHALL remove all registered hooks."""
        manager = LifecycleManager()
        
        for i in range(num_hooks):
            def hook():
                pass
            hook.__name__ = f"hook_{i}"
            manager.on_startup(hook)
            manager.on_shutdown(hook)
        
        # Clear
        manager.clear_hooks()
        
        hooks = manager.get_hooks()
        assert len(hooks["startup"]) == 0
        assert len(hooks["shutdown"]) == 0
        assert len(hooks["async_startup"]) == 0
        assert len(hooks["async_shutdown"]) == 0


class TestAsyncLifecycleHooks:
    """Tests for async lifecycle hooks."""

    @pytest.mark.asyncio
    async def test_async_shutdown_error_aggregation(self):
        """Async shutdown SHALL aggregate errors from multiple failures."""
        manager = LifecycleManager()
        executed: list[str] = []
        
        async def hook1():
            executed.append("hook1")
            raise RuntimeError("Hook 1 failed")
        hook1.__name__ = "hook1"
        
        async def hook2():
            executed.append("hook2")
        hook2.__name__ = "hook2"
        
        async def hook3():
            executed.append("hook3")
            raise RuntimeError("Hook 3 failed")
        hook3.__name__ = "hook3"
        
        manager.on_shutdown_async(hook1)
        manager.on_shutdown_async(hook2)
        manager.on_shutdown_async(hook3)
        
        with pytest.raises(LifecycleHookError) as exc_info:
            await manager.run_shutdown_async()
        
        # All hooks should have been attempted (in reverse order)
        assert len(executed) == 3
        assert executed == ["hook3", "hook2", "hook1"]
        
        # Should have 2 errors
        assert len(exc_info.value.errors) == 2
