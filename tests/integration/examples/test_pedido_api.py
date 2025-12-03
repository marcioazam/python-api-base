"""Integration tests for PedidoExample API.

**Feature: application-common-integration**
**Validates: Requirements 9.3**
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock


class TestPedidoExampleCRUD:
    """Integration tests for PedidoExample CRUD operations."""

    def test_create_pedido_command_structure(self) -> None:
        """Test CreatePedidoCommand has correct structure."""
        from application.examples.pedido.commands import CreatePedidoCommand
        
        command = CreatePedidoCommand(
            customer_id="cust-123",
            customer_name="John Doe",
            customer_email="john@example.com",
            shipping_address="123 Main St",
            notes="Rush order",
            created_by="test-user",
        )
        
        assert command.customer_id == "cust-123"
        assert command.customer_name == "John Doe"
        assert command.customer_email == "john@example.com"
        assert command.command_type == "CreatePedidoCommand"

    def test_add_item_to_pedido_command_structure(self) -> None:
        """Test AddItemToPedidoCommand has correct structure."""
        from application.examples.pedido.commands import AddItemToPedidoCommand
        
        command = AddItemToPedidoCommand(
            pedido_id="pedido-123",
            item_id="item-456",
            quantity=2,
            discount=Decimal("5.00"),
        )
        
        assert command.pedido_id == "pedido-123"
        assert command.item_id == "item-456"
        assert command.quantity == 2
        assert command.discount == Decimal("5.00")

    def test_confirm_pedido_command_structure(self) -> None:
        """Test ConfirmPedidoCommand has correct structure."""
        from application.examples.pedido.commands import ConfirmPedidoCommand
        
        command = ConfirmPedidoCommand(
            pedido_id="pedido-123",
            confirmed_by="manager",
        )
        
        assert command.pedido_id == "pedido-123"
        assert command.confirmed_by == "manager"

    def test_cancel_pedido_command_structure(self) -> None:
        """Test CancelPedidoCommand has correct structure."""
        from application.examples.pedido.commands import CancelPedidoCommand
        
        command = CancelPedidoCommand(
            pedido_id="pedido-123",
            reason="Customer request",
            cancelled_by="support",
        )
        
        assert command.pedido_id == "pedido-123"
        assert command.reason == "Customer request"
        assert command.cancelled_by == "support"


class TestPedidoExampleQueries:
    """Integration tests for PedidoExample query operations."""

    def test_get_pedido_query_structure(self) -> None:
        """Test GetPedidoQuery has correct structure."""
        from application.examples.pedido.queries import GetPedidoQuery
        
        query = GetPedidoQuery(pedido_id="pedido-123")
        
        assert query.pedido_id == "pedido-123"
        assert query.query_type == "GetPedidoQuery"

    def test_list_pedidos_query_structure(self) -> None:
        """Test ListPedidosQuery has correct structure."""
        from application.examples.pedido.queries import ListPedidosQuery
        
        query = ListPedidosQuery(
            page=1,
            size=20,
            customer_id="cust-123",
            status="pending",
            tenant_id="tenant-1",
        )
        
        assert query.page == 1
        assert query.size == 20
        assert query.customer_id == "cust-123"
        assert query.status == "pending"
        assert query.tenant_id == "tenant-1"


class TestPedidoExampleMapper:
    """Integration tests for PedidoExample mapper."""

    def test_mapper_implements_imapper(self) -> None:
        """Test PedidoExampleMapper implements IMapper interface."""
        from application.examples.pedido.mapper import PedidoExampleMapper
        from application.common.base.mapper import IMapper
        
        mapper = PedidoExampleMapper()
        
        assert hasattr(mapper, "to_dto")
        assert hasattr(mapper, "to_entity")
        assert hasattr(mapper, "to_dto_list")
        assert hasattr(mapper, "to_entity_list")


class TestPedidoExampleLifecycle:
    """Integration tests for order lifecycle."""

    def test_pedido_status_enum_values(self) -> None:
        """Test pedido status enum has expected values."""
        from domain.examples.pedido.entity import PedidoStatus
        
        # Verify status enum values exist
        assert hasattr(PedidoStatus, "PENDING")
        assert hasattr(PedidoStatus, "CONFIRMED")
        assert hasattr(PedidoStatus, "PROCESSING")
        assert hasattr(PedidoStatus, "SHIPPED")
        assert hasattr(PedidoStatus, "DELIVERED")
        assert hasattr(PedidoStatus, "CANCELLED")

    def test_pedido_commands_structure(self) -> None:
        """Test pedido commands have correct structure."""
        from decimal import Decimal
        from application.examples.pedido.commands import (
            CreatePedidoCommand,
            AddItemToPedidoCommand,
        )
        
        # Test CreatePedidoCommand
        create_cmd = CreatePedidoCommand(
            customer_id="cust-123",
            customer_name="John Doe",
            customer_email="john@example.com",
        )
        assert create_cmd.customer_id == "cust-123"
        
        # Test AddItemToPedidoCommand
        add_item_cmd = AddItemToPedidoCommand(
            pedido_id="pedido-123",
            item_id="item-1",
            quantity=2,
        )
        assert add_item_cmd.pedido_id == "pedido-123"
        assert add_item_cmd.quantity == 2


class TestPedidoExampleValidation:
    """Integration tests for pedido validation."""

    def test_create_pedido_validator(self) -> None:
        """Test CreatePedidoCommand validation."""
        from application.examples.pedido.commands import CreatePedidoCommand
        from infrastructure.di.examples_bootstrap import CreatePedidoCommandValidator
        
        # Valid command
        valid_command = CreatePedidoCommand(
            customer_id="cust-123",
            customer_name="John Doe",
            customer_email="john@example.com",
        )
        
        validator = CreatePedidoCommandValidator()
        errors = validator.validate(valid_command)
        assert len(errors) == 0
        
        # Invalid command - empty customer_id
        invalid_command = CreatePedidoCommand(
            customer_id="",
            customer_name="John Doe",
            customer_email="john@example.com",
        )
        
        errors = validator.validate(invalid_command)
        assert "Customer ID is required" in errors

    def test_email_validation(self) -> None:
        """Test email format validation."""
        from application.examples.pedido.commands import CreatePedidoCommand
        from infrastructure.di.examples_bootstrap import CreatePedidoCommandValidator
        
        command = CreatePedidoCommand(
            customer_id="cust-123",
            customer_name="John Doe",
            customer_email="invalid-email",
        )
        
        validator = CreatePedidoCommandValidator()
        errors = validator.validate(command)
        assert "Invalid email format" in errors
