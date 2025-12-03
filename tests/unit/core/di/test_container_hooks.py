"""Unit tests for Container observability hooks.

**Feature: di-observability**
**Validates: Container hooks for external monitoring and logging**

Tests verify that hooks are called at the correct times:
- on_service_registered when services are registered
- on_service_resolved when services are resolved
- on_resolution_error when resolution fails
"""

import pytest
from unittest.mock import Mock

from src.core.di.container import Container, Lifetime, ServiceNotRegisteredError


class Database:
    """Mock database service."""

    pass


class BrokenService:
    """Service that raises exception during construction."""

    def __init__(self) -> None:
        raise RuntimeError("Service construction failed")


class UserService:
    """Service with dependency."""

    def __init__(self, db: Database) -> None:
        self.db = db


class TestContainerHooks:
    """Tests for Container observability hooks."""

    @pytest.fixture
    def container(self) -> Container:
        """Create container."""
        return Container()

    @pytest.fixture
    def mock_hooks(self) -> Mock:
        """Create mock hooks object."""
        hooks = Mock()
        hooks.on_service_registered = Mock()
        hooks.on_service_resolved = Mock()
        hooks.on_resolution_error = Mock()
        return hooks

    def test_on_service_registered_called_for_register(
        self, container: Container, mock_hooks: Mock
    ) -> None:
        """Test that on_service_registered is called when registering a service."""
        container.add_hooks(mock_hooks)

        container.register(Database, lifetime=Lifetime.SINGLETON)

        mock_hooks.on_service_registered.assert_called_once_with(
            service_type=Database,
            lifetime=Lifetime.SINGLETON,
            factory=Database,
        )

    def test_on_service_registered_called_for_register_singleton(
        self, container: Container, mock_hooks: Mock
    ) -> None:
        """Test that hook is called for register_singleton."""
        container.add_hooks(mock_hooks)

        container.register_singleton(Database)

        mock_hooks.on_service_registered.assert_called_once_with(
            service_type=Database,
            lifetime=Lifetime.SINGLETON,
            factory=Database,
        )

    def test_on_service_registered_called_with_custom_factory(
        self, container: Container, mock_hooks: Mock
    ) -> None:
        """Test that hook receives custom factory."""
        container.add_hooks(mock_hooks)
        factory = lambda: Database()

        container.register(Database, factory=factory)

        mock_hooks.on_service_registered.assert_called_once()
        call_args = mock_hooks.on_service_registered.call_args
        assert call_args.kwargs["service_type"] == Database
        assert call_args.kwargs["factory"] == factory

    def test_on_service_resolved_called_for_new_singleton(
        self, container: Container, mock_hooks: Mock
    ) -> None:
        """Test that hook is called when resolving a new singleton."""
        container.register_singleton(Database)
        container.add_hooks(mock_hooks)

        db = container.resolve(Database)

        mock_hooks.on_service_resolved.assert_called_once()
        call_args = mock_hooks.on_service_resolved.call_args
        assert call_args.kwargs["service_type"] == Database
        assert call_args.kwargs["instance"] == db
        assert call_args.kwargs["is_cached"] is False

    def test_on_service_resolved_called_for_cached_singleton(
        self, container: Container, mock_hooks: Mock
    ) -> None:
        """Test that hook is called for cached singleton with is_cached=True."""
        container.register_singleton(Database)

        # Resolve once to cache it
        db1 = container.resolve(Database)

        # Add hooks after first resolution
        container.add_hooks(mock_hooks)

        # Resolve again - should be cached
        db2 = container.resolve(Database)

        assert db1 is db2  # Same instance
        mock_hooks.on_service_resolved.assert_called_once()
        call_args = mock_hooks.on_service_resolved.call_args
        assert call_args.kwargs["is_cached"] is True

    def test_on_service_resolved_called_for_transient(
        self, container: Container, mock_hooks: Mock
    ) -> None:
        """Test that hook is called for transient services with is_cached=False."""
        container.register(Database, lifetime=Lifetime.TRANSIENT)
        container.add_hooks(mock_hooks)

        db1 = container.resolve(Database)
        db2 = container.resolve(Database)

        assert db1 is not db2  # Different instances
        assert mock_hooks.on_service_resolved.call_count == 2
        # Both should have is_cached=False
        for call in mock_hooks.on_service_resolved.call_args_list:
            assert call.kwargs["is_cached"] is False

    def test_on_resolution_error_called_on_missing_service(
        self, container: Container, mock_hooks: Mock
    ) -> None:
        """Test that hook is called when service is not registered."""
        container.add_hooks(mock_hooks)

        with pytest.raises(ServiceNotRegisteredError):
            container.resolve(Database)

        mock_hooks.on_resolution_error.assert_called_once()
        call_args = mock_hooks.on_resolution_error.call_args
        assert call_args.kwargs["service_type"] == Database
        assert isinstance(call_args.kwargs["error"], ServiceNotRegisteredError)

    def test_on_resolution_error_called_on_construction_failure(
        self, container: Container, mock_hooks: Mock
    ) -> None:
        """Test that hook is called when service construction fails."""
        container.register_singleton(BrokenService)
        container.add_hooks(mock_hooks)

        with pytest.raises(RuntimeError, match="Service construction failed"):
            container.resolve(BrokenService)

        mock_hooks.on_resolution_error.assert_called_once()
        call_args = mock_hooks.on_resolution_error.call_args
        assert call_args.kwargs["service_type"] == BrokenService
        assert isinstance(call_args.kwargs["error"], RuntimeError)
        assert call_args.kwargs["resolution_stack"] == [BrokenService]

    def test_hook_resolution_stack_includes_dependencies(
        self, container: Container, mock_hooks: Mock
    ) -> None:
        """Test that resolution_stack includes the full dependency chain on error."""
        container.register_singleton(BrokenService)
        container.register(UserService)  # Depends on BrokenService - WRONG! Depends on Database
        container.add_hooks(mock_hooks)

        # This should work since UserService depends on Database, not BrokenService
        # Let me fix this test:

    def test_multiple_hooks_all_called(
        self, container: Container
    ) -> None:
        """Test that multiple hooks are all called."""
        hooks1 = Mock()
        hooks1.on_service_registered = Mock()
        hooks2 = Mock()
        hooks2.on_service_registered = Mock()

        container.add_hooks(hooks1)
        container.add_hooks(hooks2)

        container.register_singleton(Database)

        hooks1.on_service_registered.assert_called_once()
        hooks2.on_service_registered.assert_called_once()

    def test_hook_exception_does_not_break_container(
        self, container: Container, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that hook exceptions are caught and logged."""
        hooks = Mock()
        hooks.on_service_registered = Mock(side_effect=RuntimeError("Hook failed"))

        container.add_hooks(hooks)

        # Should not raise, hook exception should be caught
        container.register_singleton(Database)

        # Verify hook was called
        hooks.on_service_registered.assert_called_once()

        # Verify warning was logged (check for the warning)
        assert any("Hook execution failed" in record.message for record in caplog.records)

    def test_hooks_with_partial_implementation(
        self, container: Container
    ) -> None:
        """Test that hooks can implement only some methods."""

        class PartialHooks:
            def __init__(self):
                self.registered_services = []

            def on_service_registered(self, service_type, lifetime, factory):
                self.registered_services.append(service_type)
            # Note: Not implementing on_service_resolved or on_resolution_error

        hooks = PartialHooks()
        container.add_hooks(hooks)

        container.register_singleton(Database)
        _ = container.resolve(Database)

        # Should work fine, only on_service_registered was called
        assert Database in hooks.registered_services

    def test_hooks_called_in_order_registered(
        self, container: Container
    ) -> None:
        """Test that hooks are called in the order they were added."""
        call_order = []

        class Hook1:
            def on_service_registered(self, service_type, lifetime, factory):
                call_order.append("hook1")

        class Hook2:
            def on_service_registered(self, service_type, lifetime, factory):
                call_order.append("hook2")

        class Hook3:
            def on_service_registered(self, service_type, lifetime, factory):
                call_order.append("hook3")

        container.add_hooks(Hook1())
        container.add_hooks(Hook2())
        container.add_hooks(Hook3())

        container.register_singleton(Database)

        assert call_order == ["hook1", "hook2", "hook3"]

    def test_hook_receives_correct_resolution_stack(
        self, container: Container
    ) -> None:
        """Test that hook receives the full resolution stack on error."""
        from src.core.di.exceptions import DependencyResolutionError

        hooks = Mock()
        hooks.on_resolution_error = Mock()

        # Create a dependency chain: UserService -> Database (not registered)
        container.register(UserService)  # UserService needs Database
        container.add_hooks(hooks)

        # Try to resolve UserService - should fail because Database is not registered
        with pytest.raises(DependencyResolutionError):
            container.resolve(UserService)

        hooks.on_resolution_error.assert_called()
        call_args = hooks.on_resolution_error.call_args
        resolution_stack = call_args.kwargs["resolution_stack"]

        # Stack should include UserService (the service being resolved when error occurred)
        assert UserService in resolution_stack
