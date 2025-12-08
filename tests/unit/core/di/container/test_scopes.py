"""Tests for DI container scopes module.

Tests for Scope class.
"""

from unittest.mock import MagicMock

import pytest

from core.di.container.scopes import Scope
from core.di.lifecycle import Lifetime, Registration
from core.di.resolution import CircularDependencyError, ServiceNotRegisteredError


class SampleService:
    """Sample service for testing."""

    pass


class AnotherService:
    """Another sample service for testing."""

    pass


class DisposableService:
    """Service with dispose method."""

    def __init__(self) -> None:
        self.disposed = False

    def dispose(self) -> None:
        self.disposed = True


class CloseableService:
    """Service with close method."""

    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class TestScope:
    """Tests for Scope class."""

    def test_init_stores_parent(self) -> None:
        """Scope should store parent container."""
        parent = MagicMock()
        scope = Scope(parent)
        assert scope._parent is parent

    def test_init_empty_scoped_instances(self) -> None:
        """Scope should start with empty scoped instances."""
        parent = MagicMock()
        scope = Scope(parent)
        assert scope._scoped_instances == {}

    def test_init_empty_resolution_stack(self) -> None:
        """Scope should start with empty resolution stack."""
        parent = MagicMock()
        scope = Scope(parent)
        assert scope._resolution_stack == []

    def test_resolve_raises_when_not_registered(self) -> None:
        """resolve should raise ServiceNotRegisteredError when not registered."""
        parent = MagicMock()
        parent.is_registered.return_value = False
        scope = Scope(parent)

        with pytest.raises(ServiceNotRegisteredError):
            scope.resolve(SampleService)

    def test_resolve_singleton_delegates_to_parent(self) -> None:
        """resolve should delegate singleton resolution to parent."""
        parent = MagicMock()
        parent.is_registered.return_value = True
        registration = Registration(
            service_type=SampleService,
            factory=SampleService,
            lifetime=Lifetime.SINGLETON,
        )
        parent.get_registration.return_value = registration
        expected_instance = SampleService()
        parent.resolve.return_value = expected_instance
        scope = Scope(parent)

        result = scope.resolve(SampleService)

        assert result is expected_instance
        parent.resolve.assert_called_once_with(SampleService)

    def test_resolve_scoped_creates_instance_once(self) -> None:
        """resolve should create scoped instance only once."""
        parent = MagicMock()
        parent.is_registered.return_value = True
        registration = Registration(
            service_type=SampleService,
            factory=SampleService,
            lifetime=Lifetime.SCOPED,
        )
        parent.get_registration.return_value = registration
        instance = SampleService()
        parent.create_instance.return_value = instance
        scope = Scope(parent)

        result1 = scope.resolve(SampleService)
        result2 = scope.resolve(SampleService)

        assert result1 is instance
        assert result2 is instance
        # create_instance should only be called once
        assert parent.create_instance.call_count == 1

    def test_resolve_transient_creates_new_instance(self) -> None:
        """resolve should create new instance for transient services."""
        parent = MagicMock()
        parent.is_registered.return_value = True
        registration = Registration(
            service_type=SampleService,
            factory=SampleService,
            lifetime=Lifetime.TRANSIENT,
        )
        parent.get_registration.return_value = registration
        parent.create_instance.side_effect = [SampleService(), SampleService()]
        scope = Scope(parent)

        result1 = scope.resolve(SampleService)
        result2 = scope.resolve(SampleService)

        assert result1 is not result2
        assert parent.create_instance.call_count == 2

    def test_resolve_detects_circular_dependency(self) -> None:
        """resolve should detect circular dependencies."""
        parent = MagicMock()
        parent.is_registered.return_value = True
        registration = Registration(
            service_type=SampleService,
            factory=SampleService,
            lifetime=Lifetime.SCOPED,
        )
        parent.get_registration.return_value = registration
        scope = Scope(parent)
        # Simulate circular dependency by adding to resolution stack
        scope._resolution_stack.append(SampleService)

        with pytest.raises(CircularDependencyError):
            scope.resolve(SampleService)

    def test_dispose_calls_dispose_on_instances(self) -> None:
        """dispose should call dispose() on scoped instances."""
        parent = MagicMock()
        scope = Scope(parent)
        service = DisposableService()
        scope._scoped_instances[DisposableService] = service

        scope.dispose()

        assert service.disposed is True
        assert scope._scoped_instances == {}

    def test_dispose_calls_close_on_instances(self) -> None:
        """dispose should call close() on instances without dispose()."""
        parent = MagicMock()
        scope = Scope(parent)
        service = CloseableService()
        scope._scoped_instances[CloseableService] = service

        scope.dispose()

        assert service.closed is True
        assert scope._scoped_instances == {}

    def test_dispose_clears_scoped_instances(self) -> None:
        """dispose should clear all scoped instances."""
        parent = MagicMock()
        scope = Scope(parent)
        scope._scoped_instances[SampleService] = SampleService()
        scope._scoped_instances[AnotherService] = AnotherService()

        scope.dispose()

        assert scope._scoped_instances == {}

    def test_dispose_handles_instances_without_cleanup_methods(self) -> None:
        """dispose should handle instances without dispose/close methods."""
        parent = MagicMock()
        scope = Scope(parent)
        scope._scoped_instances[SampleService] = SampleService()

        # Should not raise
        scope.dispose()

        assert scope._scoped_instances == {}
