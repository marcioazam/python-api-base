"""FastAPI dependency injection utilities.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 5.5**
"""

from typing import Annotated

from fastapi import Depends, Request

from core.config.settings import Settings, get_settings
from application.common.bus import CommandBus, QueryBus


# Settings dependency
def get_app_settings() -> Settings:
    """Get application settings singleton."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


# Command Bus dependency
_command_bus: CommandBus | None = None


def get_command_bus() -> CommandBus:
    """Get CommandBus singleton.

    Returns:
        CommandBus instance with registered handlers.
    """
    global _command_bus
    if _command_bus is None:
        _command_bus = CommandBus()
        # TODO: Register handlers here or via DI container
    return _command_bus


CommandBusDep = Annotated[CommandBus, Depends(get_command_bus)]


# Query Bus dependency
_query_bus: QueryBus | None = None


def get_query_bus() -> QueryBus:
    """Get QueryBus singleton.

    Returns:
        QueryBus instance with registered handlers.
    """
    global _query_bus
    if _query_bus is None:
        _query_bus = QueryBus()
        # TODO: Register handlers here or via DI container
    return _query_bus


QueryBusDep = Annotated[QueryBus, Depends(get_query_bus)]


# Correlation ID dependency
def get_correlation_id(request: Request) -> str:
    """Extract or generate correlation ID from request.

    Args:
        request: FastAPI request object.

    Returns:
        Correlation ID string.
    """
    correlation_id = request.headers.get("X-Correlation-ID")
    if not correlation_id:
        import uuid

        correlation_id = str(uuid.uuid4())
    return correlation_id


CorrelationIdDep = Annotated[str, Depends(get_correlation_id)]


# Pagination dependency
def get_pagination_params(
    page: int = 1,
    page_size: int = 20,
) -> dict[str, int]:
    """Get pagination parameters.

    Args:
        page: Page number (1-indexed).
        page_size: Items per page (max 100).

    Returns:
        Dictionary with page and page_size.
    """
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    return {"page": page, "page_size": page_size}


PaginationDep = Annotated[dict[str, int], Depends(get_pagination_params)]
