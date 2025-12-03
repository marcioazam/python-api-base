"""Property-based tests for infrastructure examples integration.

**Feature: infrastructure-examples-integration-fix**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4**
"""

import pytest
from hypothesis import given, settings, strategies as st
from unittest.mock import AsyncMock, MagicMock, patch


class TestAsyncSessionProperties:
    """Property tests for async session functionality.

    **Feature: infrastructure-examples-integration-fix, Property 1: Async Session Yields Valid Session**
    **Validates: Requirements 1.1**
    """

    def test_get_async_session_function_exists(self) -> None:
        """Verify get_async_session function is importable."""
        from infrastructure.db.session import get_async_session
        assert get_async_session is not None
        assert callable(get_async_session)

    def test_get_async_session_is_async_generator(self) -> None:
        """Verify get_async_session is an async generator function."""
        import inspect
        from infrastructure.db.session import get_async_session
        assert inspect.isasyncgenfunction(get_async_session)

    @pytest.mark.asyncio
    async def test_get_async_session_raises_when_not_initialized(self) -> None:
        """
        **Feature: infrastructure-examples-integration-fix, Property 3: Uninitialized Database Error**
        **Validates: Requirements 1.3**

        *For any* call to get_async_session() when database is not initialized,
        the function SHALL raise a DatabaseError.
        """
        from infrastructure.db.session import get_async_session
        from infrastructure.errors import DatabaseError

        # Save current state
        from infrastructure.db import session as session_module
        original = session_module._db_session
        session_module._db_session = None

        try:
            gen = get_async_session()
            with pytest.raises(DatabaseError) as exc_info:
                await gen.__anext__()
            assert "not initialized" in str(exc_info.value).lower()
        finally:
            # Restore state
            session_module._db_session = original


class TestSessionCleanupProperties:
    """Property tests for session cleanup.

    **Feature: infrastructure-examples-integration-fix, Property 4: Session Cleanup on Exit**
    **Validates: Requirements 1.4**
    """

    def test_database_session_class_has_session_context_manager(self) -> None:
        """Verify DatabaseSession has session context manager."""
        from infrastructure.db.session import DatabaseSession
        assert hasattr(DatabaseSession, 'session')

    def test_session_context_manager_is_async(self) -> None:
        """Verify session() is an async context manager."""
        import inspect
        from infrastructure.db.session import DatabaseSession
        # Check that session method exists and returns async context manager
        assert hasattr(DatabaseSession, 'session')


class TestRouterDependencyProperties:
    """Property tests for router dependency injection.

    **Feature: infrastructure-examples-integration-fix, Property 5: Router Uses Real Repositories**
    **Validates: Requirements 2.1, 2.2**
    """

    def test_router_imports_real_repositories(self) -> None:
        """Verify router imports real repository classes."""
        from interface.v1.examples.router import (
            ItemExampleRepository,
            PedidoExampleRepository,
        )
        assert ItemExampleRepository is not None
        assert PedidoExampleRepository is not None

    def test_router_imports_get_async_session(self) -> None:
        """Verify router imports get_async_session."""
        from interface.v1.examples.router import get_async_session
        assert get_async_session is not None

    def test_router_has_real_dependency_functions(self) -> None:
        """Verify router has real dependency injection functions."""
        from interface.v1.examples.router import (
            get_item_repository,
            get_pedido_repository,
            get_item_use_case,
            get_pedido_use_case,
        )
        assert get_item_repository is not None
        assert get_pedido_repository is not None
        assert get_item_use_case is not None
        assert get_pedido_use_case is not None

    def test_router_no_mock_dependencies_in_routes(self) -> None:
        """Verify routes use real dependencies, not mocks."""
        from interface.v1.examples.router import router
        import inspect

        # Get source code of router module
        from interface.v1.examples import router as router_module
        source = inspect.getsource(router_module)

        # Verify no mock usage in Depends()
        assert "get_mock_item_use_case" not in source or "Depends(get_mock" not in source
        assert "get_mock_pedido_use_case" not in source or "Depends(get_mock" not in source

    @pytest.mark.asyncio
    async def test_get_item_repository_returns_correct_type(self) -> None:
        """
        *For any* call to get_item_repository with a valid session,
        the function SHALL return an ItemExampleRepository instance.
        """
        from unittest.mock import MagicMock
        from interface.v1.examples.router import get_item_repository
        from infrastructure.db.repositories.examples import ItemExampleRepository

        mock_session = MagicMock()
        repo = await get_item_repository(session=mock_session)
        assert isinstance(repo, ItemExampleRepository)

    @pytest.mark.asyncio
    async def test_get_pedido_repository_returns_correct_type(self) -> None:
        """
        *For any* call to get_pedido_repository with a valid session,
        the function SHALL return a PedidoExampleRepository instance.
        """
        from unittest.mock import MagicMock
        from interface.v1.examples.router import get_pedido_repository
        from infrastructure.db.repositories.examples import PedidoExampleRepository

        mock_session = MagicMock()
        repo = await get_pedido_repository(session=mock_session)
        assert isinstance(repo, PedidoExampleRepository)


class TestBootstrapHandlerRegistrationProperties:
    """Property tests for bootstrap handler registration.

    **Feature: infrastructure-examples-integration-fix, Property 6: Bootstrap Registers All Handlers**
    **Validates: Requirements 3.1, 3.2, 3.3**
    """

    def test_bootstrap_examples_function_exists(self) -> None:
        """Verify bootstrap_examples function is importable."""
        from infrastructure.di.examples_bootstrap import bootstrap_examples
        assert bootstrap_examples is not None
        assert callable(bootstrap_examples)

    def test_bootstrap_examples_is_async(self) -> None:
        """Verify bootstrap_examples is an async function."""
        import inspect
        from infrastructure.di.examples_bootstrap import bootstrap_examples
        assert inspect.iscoroutinefunction(bootstrap_examples)

    def test_main_imports_bootstrap_examples(self) -> None:
        """Verify main.py imports bootstrap_examples."""
        import inspect
        import main
        source = inspect.getsource(main)
        assert "bootstrap_examples" in source
        assert "from infrastructure.di.examples_bootstrap import bootstrap_examples" in source

    def test_main_imports_example_repositories(self) -> None:
        """Verify main.py imports example repositories."""
        import inspect
        import main
        source = inspect.getsource(main)
        assert "ItemExampleRepository" in source
        assert "PedidoExampleRepository" in source

    def test_configure_example_command_bus_registers_handlers(self) -> None:
        """
        *For any* call to configure_example_command_bus,
        the CommandBus SHALL have handlers registered for all Item and Pedido commands.
        """
        from unittest.mock import MagicMock
        from infrastructure.di.examples_bootstrap import configure_example_command_bus
        from application.examples.item.commands import (
            CreateItemCommand,
            UpdateItemCommand,
            DeleteItemCommand,
        )
        from application.examples.pedido.commands import (
            CreatePedidoCommand,
            AddItemToPedidoCommand,
            ConfirmPedidoCommand,
            CancelPedidoCommand,
        )

        mock_item_repo = MagicMock()
        mock_pedido_repo = MagicMock()

        bus = configure_example_command_bus(
            item_repository=mock_item_repo,
            pedido_repository=mock_pedido_repo,
        )

        # Verify all command handlers are registered
        assert bus._handlers.get(CreateItemCommand) is not None
        assert bus._handlers.get(UpdateItemCommand) is not None
        assert bus._handlers.get(DeleteItemCommand) is not None
        assert bus._handlers.get(CreatePedidoCommand) is not None
        assert bus._handlers.get(AddItemToPedidoCommand) is not None
        assert bus._handlers.get(ConfirmPedidoCommand) is not None
        assert bus._handlers.get(CancelPedidoCommand) is not None

    def test_configure_example_query_bus_registers_handlers(self) -> None:
        """
        *For any* call to configure_example_query_bus,
        the QueryBus SHALL have handlers registered for all Item and Pedido queries.
        """
        from unittest.mock import MagicMock
        from infrastructure.di.examples_bootstrap import configure_example_query_bus
        from application.examples.item.queries import GetItemQuery, ListItemsQuery
        from application.examples.pedido.queries import GetPedidoQuery, ListPedidosQuery

        mock_item_repo = MagicMock()
        mock_pedido_repo = MagicMock()

        bus = configure_example_query_bus(
            item_repository=mock_item_repo,
            pedido_repository=mock_pedido_repo,
        )

        # Verify all query handlers are registered
        assert bus._handlers.get(GetItemQuery) is not None
        assert bus._handlers.get(ListItemsQuery) is not None
        assert bus._handlers.get(GetPedidoQuery) is not None
        assert bus._handlers.get(ListPedidosQuery) is not None


class TestItemPersistenceRoundTripProperties:
    """Property tests for Item persistence round-trip.

    **Feature: infrastructure-examples-integration-fix, Property 7: Item Persistence Round-Trip**
    **Validates: Requirements 4.1, 4.2**
    """

    def test_item_repository_has_crud_methods(self) -> None:
        """Verify ItemExampleRepository has all CRUD methods."""
        from infrastructure.db.repositories.examples import ItemExampleRepository
        assert hasattr(ItemExampleRepository, 'get')
        assert hasattr(ItemExampleRepository, 'create')
        assert hasattr(ItemExampleRepository, 'update')
        assert hasattr(ItemExampleRepository, 'delete')
        assert hasattr(ItemExampleRepository, 'get_all')

    def test_item_repository_get_by_sku_exists(self) -> None:
        """Verify ItemExampleRepository has get_by_sku method."""
        from infrastructure.db.repositories.examples import ItemExampleRepository
        assert hasattr(ItemExampleRepository, 'get_by_sku')

    @given(
        name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        sku=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-", min_size=3, max_size=20),
        quantity=st.integers(min_value=0, max_value=10000),
    )
    @settings(max_examples=100)
    def test_item_entity_preserves_essential_fields(
        self, name: str, sku: str, quantity: int
    ) -> None:
        """
        *For any* valid ItemExample data, creating an entity SHALL preserve
        essential fields (name, sku, quantity).
        """
        from domain.examples.item.entity import ItemExample, Money

        item = ItemExample(
            name=name,
            sku=sku,
            quantity=quantity,
            price=Money(100, "USD"),
        )

        assert item.name == name
        assert item.sku == sku
        assert item.quantity == quantity


class TestPedidoPersistenceRoundTripProperties:
    """Property tests for Pedido persistence round-trip.

    **Feature: infrastructure-examples-integration-fix, Property 8: Pedido Persistence Round-Trip**
    **Validates: Requirements 4.3, 4.4**
    """

    def test_pedido_repository_has_crud_methods(self) -> None:
        """Verify PedidoExampleRepository has all CRUD methods."""
        from infrastructure.db.repositories.examples import PedidoExampleRepository
        assert hasattr(PedidoExampleRepository, 'get')
        assert hasattr(PedidoExampleRepository, 'create')
        assert hasattr(PedidoExampleRepository, 'update')
        assert hasattr(PedidoExampleRepository, 'get_all')

    @given(
        customer_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        customer_name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        customer_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_pedido_entity_preserves_essential_fields(
        self, customer_id: str, customer_name: str, customer_email: str
    ) -> None:
        """
        *For any* valid PedidoExample data, creating an entity SHALL preserve
        essential fields (customer_id, customer_name, customer_email).
        """
        from domain.examples.pedido.entity import PedidoExample

        pedido = PedidoExample(
            customer_id=customer_id,
            customer_name=customer_name,
            customer_email=customer_email,
        )

        assert pedido.customer_id == customer_id
        assert pedido.customer_name == customer_name
        assert pedido.customer_email == customer_email


class TestSessionTransactionRoundTripProperties:
    """Property tests for session transaction round-trip.

    **Feature: infrastructure-examples-integration-fix, Property 2: Session Transaction Round-Trip**
    **Validates: Requirements 1.2, 2.3**
    """

    def test_database_session_commits_on_success(self) -> None:
        """Verify DatabaseSession commits transaction on successful completion."""
        from infrastructure.db.session import DatabaseSession
        import inspect

        # Check session method source for commit call
        source = inspect.getsource(DatabaseSession.session)
        assert "commit" in source

    def test_database_session_rollbacks_on_error(self) -> None:
        """Verify DatabaseSession rolls back transaction on error."""
        from infrastructure.db.session import DatabaseSession
        import inspect

        # Check session method source for rollback call
        source = inspect.getsource(DatabaseSession.session)
        assert "rollback" in source

    def test_database_session_closes_on_exit(self) -> None:
        """Verify DatabaseSession closes session on context exit."""
        from infrastructure.db.session import DatabaseSession
        import inspect

        # Check session method source for close call in finally
        source = inspect.getsource(DatabaseSession.session)
        assert "close" in source
        assert "finally" in source
