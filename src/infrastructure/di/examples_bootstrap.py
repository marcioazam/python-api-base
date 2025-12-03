"""Examples CQRS handler registration bootstrap.

Configures CommandBus and QueryBus with middleware pipeline
and registers all example handlers.

**Feature: application-common-integration**
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**
"""

import logging
import re
from typing import Any

from application.common.cqrs import CommandBus, QueryBus
from application.common.cqrs.event_bus import TypedEventBus
from application.common.middleware.observability import LoggingMiddleware, LoggingConfig
from application.common.middleware.retry import RetryMiddleware, RetryConfig
from application.common.middleware.circuit_breaker import CircuitBreakerMiddleware, CircuitBreakerConfig
from application.common.middleware.validation import ValidationMiddleware, Validator

from application.examples.item.commands import CreateItemCommand, UpdateItemCommand, DeleteItemCommand
from application.examples.item.queries import GetItemQuery, ListItemsQuery
from application.examples.item.handlers import (
    CreateItemCommandHandler,
    UpdateItemCommandHandler,
    DeleteItemCommandHandler,
    GetItemQueryHandler,
    ListItemsQueryHandler,
    IItemRepository,
)

from application.examples.pedido.commands import (
    CreatePedidoCommand,
    AddItemToPedidoCommand,
    ConfirmPedidoCommand,
    CancelPedidoCommand,
)
from application.examples.pedido.queries import GetPedidoQuery, ListPedidosQuery
from application.examples.pedido.handlers import (
    CreatePedidoCommandHandler,
    AddItemToPedidoCommandHandler,
    ConfirmPedidoCommandHandler,
    CancelPedidoCommandHandler,
    GetPedidoQueryHandler,
    ListPedidosQueryHandler,
    IPedidoRepository,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Validators
# =============================================================================


class CreateItemCommandValidator(Validator[CreateItemCommand]):
    """Validator for CreateItemCommand."""

    def validate(self, command: CreateItemCommand) -> list[str]:
        """Validate create item command."""
        errors: list[str] = []
        
        if not command.name or not command.name.strip():
            errors.append("Name is required")
        
        if not command.sku or not command.sku.strip():
            errors.append("SKU is required")
        elif not re.match(r"^[A-Z0-9-]+$", command.sku):
            errors.append("SKU must contain only uppercase letters, numbers, and hyphens")
        
        if command.price_amount < 0:
            errors.append("Price must be non-negative")
        
        if command.quantity < 0:
            errors.append("Quantity must be non-negative")
        
        return errors


class CreatePedidoCommandValidator(Validator[CreatePedidoCommand]):
    """Validator for CreatePedidoCommand."""

    def validate(self, command: CreatePedidoCommand) -> list[str]:
        """Validate create pedido command."""
        errors: list[str] = []
        
        if not command.customer_id or not command.customer_id.strip():
            errors.append("Customer ID is required")
        
        if not command.customer_name or not command.customer_name.strip():
            errors.append("Customer name is required")
        
        if not command.customer_email or not command.customer_email.strip():
            errors.append("Customer email is required")
        elif not re.match(r"^[^@]+@[^@]+\.[^@]+$", command.customer_email):
            errors.append("Invalid email format")
        
        return errors


# =============================================================================
# Bootstrap Functions
# =============================================================================


def configure_example_command_bus(
    item_repository: IItemRepository,
    pedido_repository: IPedidoRepository,
    event_bus: TypedEventBus[Any] | None = None,
) -> CommandBus:
    """Configure CommandBus with middleware and handlers for examples.
    
    Args:
        item_repository: Repository for ItemExample entities.
        pedido_repository: Repository for PedidoExample entities.
        event_bus: Optional event bus for publishing domain events.
    
    Returns:
        Configured CommandBus instance.
    """
    bus = CommandBus()
    
    # Configure middleware pipeline (order matters)
    bus.add_middleware(LoggingMiddleware(LoggingConfig(
        log_duration=True,
        log_request=True,
        log_response=False,
    )))
    
    # Validation middleware with validators
    validators: dict[type, Validator[Any]] = {
        CreateItemCommand: CreateItemCommandValidator(),
        CreatePedidoCommand: CreatePedidoCommandValidator(),
    }
    bus.add_middleware(ValidationMiddleware(validators))
    
    # Retry middleware for transient failures
    bus.add_middleware(RetryMiddleware(RetryConfig(
        max_retries=3,
        base_delay=0.1,
        max_delay=2.0,
        exponential_base=2.0,
    )))
    
    # Circuit breaker for cascade failure prevention
    bus.add_middleware(CircuitBreakerMiddleware(CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0,
        half_open_max_calls=3,
    )))
    
    # Register Item handlers
    create_item_handler = CreateItemCommandHandler(
        repository=item_repository,
        event_bus=event_bus,
    )
    update_item_handler = UpdateItemCommandHandler(
        repository=item_repository,
        event_bus=event_bus,
    )
    delete_item_handler = DeleteItemCommandHandler(
        repository=item_repository,
        event_bus=event_bus,
    )
    
    bus.register(CreateItemCommand, create_item_handler.handle)
    bus.register(UpdateItemCommand, update_item_handler.handle)
    bus.register(DeleteItemCommand, delete_item_handler.handle)
    
    # Register Pedido handlers
    create_pedido_handler = CreatePedidoCommandHandler(
        pedido_repository=pedido_repository,
        item_repository=item_repository,
        event_bus=event_bus,
    )
    add_item_handler = AddItemToPedidoCommandHandler(
        pedido_repository=pedido_repository,
        item_repository=item_repository,
        event_bus=event_bus,
    )
    confirm_pedido_handler = ConfirmPedidoCommandHandler(
        repository=pedido_repository,
        event_bus=event_bus,
    )
    cancel_pedido_handler = CancelPedidoCommandHandler(
        repository=pedido_repository,
        event_bus=event_bus,
    )
    
    bus.register(CreatePedidoCommand, create_pedido_handler.handle)
    bus.register(AddItemToPedidoCommand, add_item_handler.handle)
    bus.register(ConfirmPedidoCommand, confirm_pedido_handler.handle)
    bus.register(CancelPedidoCommand, cancel_pedido_handler.handle)
    
    logger.info("Example CommandBus configured with middleware and handlers")
    return bus


def configure_example_query_bus(
    item_repository: IItemRepository,
    pedido_repository: IPedidoRepository,
) -> QueryBus:
    """Configure QueryBus with handlers for examples.
    
    Args:
        item_repository: Repository for ItemExample entities.
        pedido_repository: Repository for PedidoExample entities.
    
    Returns:
        Configured QueryBus instance.
    """
    bus = QueryBus()
    
    # Register Item query handlers
    get_item_handler = GetItemQueryHandler(repository=item_repository)
    list_items_handler = ListItemsQueryHandler(repository=item_repository)
    
    bus.register(GetItemQuery, get_item_handler.handle)
    bus.register(ListItemsQuery, list_items_handler.handle)
    
    # Register Pedido query handlers
    get_pedido_handler = GetPedidoQueryHandler(repository=pedido_repository)
    list_pedidos_handler = ListPedidosQueryHandler(repository=pedido_repository)
    
    bus.register(GetPedidoQuery, get_pedido_handler.handle)
    bus.register(ListPedidosQuery, list_pedidos_handler.handle)
    
    logger.info("Example QueryBus configured with handlers")
    return bus


async def bootstrap_examples(
    command_bus: CommandBus,
    query_bus: QueryBus,
    item_repository: IItemRepository,
    pedido_repository: IPedidoRepository,
    event_bus: TypedEventBus[Any] | None = None,
) -> None:
    """Bootstrap example CQRS system.
    
    This is the main entry point for example handler registration.
    Call during application startup after database initialization.
    
    Args:
        command_bus: CommandBus instance to configure.
        query_bus: QueryBus instance to configure.
        item_repository: Repository for ItemExample entities.
        pedido_repository: Repository for PedidoExample entities.
        event_bus: Optional event bus for domain events.
    """
    logger.info("Bootstrapping example CQRS handlers...")
    
    # Configure validators
    validators: dict[type, Validator[Any]] = {
        CreateItemCommand: CreateItemCommandValidator(),
        CreatePedidoCommand: CreatePedidoCommandValidator(),
    }
    
    # Add middleware to command bus
    command_bus.add_middleware(LoggingMiddleware(LoggingConfig(log_duration=True)))
    command_bus.add_middleware(ValidationMiddleware(validators))
    command_bus.add_middleware(RetryMiddleware(RetryConfig(max_retries=3)))
    command_bus.add_middleware(CircuitBreakerMiddleware(CircuitBreakerConfig(failure_threshold=5)))
    
    # Register Item command handlers
    create_item = CreateItemCommandHandler(repository=item_repository, event_bus=event_bus)
    update_item = UpdateItemCommandHandler(repository=item_repository, event_bus=event_bus)
    delete_item = DeleteItemCommandHandler(repository=item_repository, event_bus=event_bus)
    
    command_bus.register(CreateItemCommand, create_item.handle)
    command_bus.register(UpdateItemCommand, update_item.handle)
    command_bus.register(DeleteItemCommand, delete_item.handle)
    
    # Register Pedido command handlers
    create_pedido = CreatePedidoCommandHandler(
        pedido_repository=pedido_repository,
        item_repository=item_repository,
        event_bus=event_bus,
    )
    add_item_to_pedido = AddItemToPedidoCommandHandler(
        pedido_repository=pedido_repository,
        item_repository=item_repository,
        event_bus=event_bus,
    )
    confirm_pedido = ConfirmPedidoCommandHandler(repository=pedido_repository, event_bus=event_bus)
    cancel_pedido = CancelPedidoCommandHandler(repository=pedido_repository, event_bus=event_bus)
    
    command_bus.register(CreatePedidoCommand, create_pedido.handle)
    command_bus.register(AddItemToPedidoCommand, add_item_to_pedido.handle)
    command_bus.register(ConfirmPedidoCommand, confirm_pedido.handle)
    command_bus.register(CancelPedidoCommand, cancel_pedido.handle)
    
    # Register Item query handlers
    get_item = GetItemQueryHandler(repository=item_repository)
    list_items = ListItemsQueryHandler(repository=item_repository)
    
    query_bus.register(GetItemQuery, get_item.handle)
    query_bus.register(ListItemsQuery, list_items.handle)
    
    # Register Pedido query handlers
    get_pedido = GetPedidoQueryHandler(repository=pedido_repository)
    list_pedidos = ListPedidosQueryHandler(repository=pedido_repository)
    
    query_bus.register(GetPedidoQuery, get_pedido.handle)
    query_bus.register(ListPedidosQuery, list_pedidos.handle)
    
    logger.info("Example CQRS bootstrap complete")
