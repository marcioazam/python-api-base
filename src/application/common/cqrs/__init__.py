"""CQRS infrastructure components.

Provides Command Query Responsibility Segregation pattern implementation:
- CommandBus: Dispatches commands to handlers
- QueryBus: Dispatches queries to handlers with caching
- EventBus: Publishes domain events to subscribers

**Architecture: CQRS Pattern**
"""

# Re-export from bus module (main façade)
from application.common.cqrs.bus import (
    ApplicationError,
    Command,
    CommandBus,
    CommandHandler,
    ConflictError,
    EventHandler,
    EventHandlerError,
    ForbiddenError,
    HandlerNotFoundError,
    NotFoundError,
    Query,
    QueryBus,
    QueryHandler,
    TypedEventBus,
    UnauthorizedError,
    ValidationError,
)
from application.common.cqrs.commands import MiddlewareFunc

__all__ = [
    # Exceptions
    "ApplicationError",
    # Command Bus
    "Command",
    "CommandBus",
    "CommandHandler",
    "ConflictError",
    # Event Bus
    "EventHandler",
    "EventHandlerError",
    "ForbiddenError",
    "HandlerNotFoundError",
    "MiddlewareFunc",
    "NotFoundError",
    # Query Bus
    "Query",
    "QueryBus",
    "QueryHandler",
    "TypedEventBus",
    "UnauthorizedError",
    "ValidationError",
]
