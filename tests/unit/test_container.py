"""Unit tests for dependency injection container.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
"""

import pytest
from dependency_injector import providers

from core.config import Settings
from infrastructure.di.app_container import Container, LifecycleManager, create_container


class TestContainer:
    """Unit tests for DI container."""

    def test_container_creates_config_singleton(self) -> None:
        """Container SHALL provide Settings as singleton."""
        container = Container()
        
        # Config should be a singleton provider
        assert isinstance(container.config, providers.Singleton)

    def test_container_wiring_configuration(self) -> None:
        """Container SHALL have wiring configuration for routes."""
        container = Container()
        
        # Should have wiring config
        assert container.wiring_config is not None
        assert len(container.wiring_config.modules) > 0

    def test_create_container_returns_container(self) -> None:
        """create_container SHALL return a Container instance."""
        container = create_container()
        
        # create_container returns a DynamicContainer which is a subclass
        from dependency_injector import containers
        assert isinstance(container, containers.Container)

    def test_create_container_with_settings_override(self) -> None:
        """create_container SHALL accept settings override."""
        # Create mock settings
        settings = Settings(
            app_name="Test App",
            debug=True,
        )
        
        container = create_container(settings=settings)
        
        # Config should be overridden
        assert container.config.provided is not None

    def test_container_db_session_manager_is_dependency(self) -> None:
        """Container SHALL have db_session_manager as dependency provider."""
        container = Container()
        
        assert isinstance(container.db_session_manager, providers.Dependency)


class TestLifecycleManager:
    """Unit tests for lifecycle manager."""

    def test_lifecycle_manager_registers_startup_hook(self) -> None:
        """LifecycleManager SHALL register startup hooks."""
        manager = LifecycleManager()
        
        called = []
        
        @manager.on_startup
        def startup_hook():
            called.append("startup")
        
        manager.run_startup()
        
        assert "startup" in called

    def test_lifecycle_manager_registers_shutdown_hook(self) -> None:
        """LifecycleManager SHALL register shutdown hooks."""
        manager = LifecycleManager()
        
        called = []
        
        @manager.on_shutdown
        def shutdown_hook():
            called.append("shutdown")
        
        manager.run_shutdown()
        
        assert "shutdown" in called

    def test_lifecycle_manager_runs_shutdown_in_reverse(self) -> None:
        """LifecycleManager SHALL run shutdown hooks in reverse order."""
        manager = LifecycleManager()
        
        order = []
        
        @manager.on_shutdown
        def first():
            order.append("first")
        
        @manager.on_shutdown
        def second():
            order.append("second")
        
        manager.run_shutdown()
        
        # Should be reversed
        assert order == ["second", "first"]

    @pytest.mark.asyncio
    async def test_lifecycle_manager_async_startup(self) -> None:
        """LifecycleManager SHALL support async startup hooks."""
        manager = LifecycleManager()
        
        called = []
        
        @manager.on_startup_async
        async def async_startup():
            called.append("async_startup")
        
        await manager.run_startup_async()
        
        assert "async_startup" in called

    @pytest.mark.asyncio
    async def test_lifecycle_manager_async_shutdown(self) -> None:
        """LifecycleManager SHALL support async shutdown hooks."""
        manager = LifecycleManager()
        
        called = []
        
        @manager.on_shutdown_async
        async def async_shutdown():
            called.append("async_shutdown")
        
        await manager.run_shutdown_async()
        
        assert "async_shutdown" in called

    @pytest.mark.asyncio
    async def test_lifecycle_manager_async_shutdown_reverse_order(self) -> None:
        """LifecycleManager SHALL run async shutdown hooks in reverse order."""
        manager = LifecycleManager()
        
        order = []
        
        @manager.on_shutdown_async
        async def first():
            order.append("first")
        
        @manager.on_shutdown_async
        async def second():
            order.append("second")
        
        await manager.run_shutdown_async()
        
        assert order == ["second", "first"]

    def test_lifecycle_manager_decorator_returns_function(self) -> None:
        """Lifecycle decorators SHALL return the original function."""
        manager = LifecycleManager()
        
        def my_func():
            pass
        
        result = manager.on_startup(my_func)
        
        assert result is my_func

    def test_lifecycle_manager_handles_startup_error(self) -> None:
        """LifecycleManager SHALL propagate startup errors."""
        manager = LifecycleManager()
        
        @manager.on_startup
        def failing_hook():
            raise ValueError("Startup failed")
        
        with pytest.raises(ValueError, match="Startup failed"):
            manager.run_startup()

    def test_lifecycle_manager_continues_on_shutdown_error(self) -> None:
        """LifecycleManager SHALL continue shutdown even if hook fails."""
        from infrastructure.di.app_container import LifecycleHookError

        manager = LifecycleManager()

        called = []

        @manager.on_shutdown
        def first():
            called.append("first")

        @manager.on_shutdown
        def failing():
            raise ValueError("Shutdown failed")

        @manager.on_shutdown
        def third():
            called.append("third")

        # Should raise aggregated error but continue all hooks
        with pytest.raises(LifecycleHookError):
            manager.run_shutdown()

        # Both non-failing hooks should have been called
        assert "first" in called
        assert "third" in called
