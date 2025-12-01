"""Event projections for updating read models.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 4.2, 4.4**
"""

from my_app.application.projections.users_projections import (
    UserProjectionHandler,
    UserReadModelProjector,
)

__all__ = [
    "UserProjectionHandler",
    "UserReadModelProjector",
]
