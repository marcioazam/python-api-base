"""FastAPI dependency injection utilities.

**Feature: architecture-restructuring-2025**
**Refactored: 2025 - Removed global mutable singletons, using DI container**
**Validates: Requirements 5.5**
"""

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query, Request

from core.config.settings import Settings, get_settings
from application.common.cqrs import CommandBus, QueryBus
from infrastructure.di.app_container import Container, create_container

# Container singleton (immutable after creation)
_container: Container | None = None


def _get_container() -> Container:
    """Get or create the DI container (lazy initialization)."""
    global _container
    if _container is None:
        _container = create_container()
    return _container


# Settings dependency
def get_app_settings() -> Settings:
    """Get application settings singleton."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


# Command Bus dependency - via DI container
def get_command_bus() -> CommandBus:
    """Get CommandBus from DI container.

    Returns:
        CommandBus instance with registered handlers.
    """
    return _get_container().command_bus()


CommandBusDep = Annotated[CommandBus, Depends(get_command_bus)]


# Query Bus dependency - via DI container
def get_query_bus() -> QueryBus:
    """Get QueryBus from DI container.

    Returns:
        QueryBus instance with registered handlers.
    """
    return _get_container().query_bus()


QueryBusDep = Annotated[QueryBus, Depends(get_query_bus)]


# Correlation ID dependency
def get_correlation_id(request: Request) -> str:
    """Extract or generate correlation ID from request.

    Args:
        request: FastAPI request object.

    Returns:
        Correlation ID string.
    """
    return request.headers.get("X-Correlation-ID") or str(uuid.uuid4())


CorrelationIdDep = Annotated[str, Depends(get_correlation_id)]


@dataclass(frozen=True, slots=True)
class PaginationParams:
    """Pagination parameters value object."""

    page: int
    page_size: int

    @property
    def skip(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.page_size


def get_pagination_params(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> PaginationParams:
    """Get validated pagination parameters.

    Args:
        page: Page number (1-indexed, min 1).
        page_size: Items per page (1-100).

    Returns:
        PaginationParams with validated values.
    """
    return PaginationParams(page=page, page_size=page_size)


PaginationDep = Annotated[PaginationParams, Depends(get_pagination_params)]
