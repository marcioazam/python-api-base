"""Database repository implementations (Adapters).

**Feature: architecture-restructuring-2025**
**Validates: Requirements 6.2**
"""

from my_app.infrastructure.db.repositories.user_repository import (
    SQLAlchemyUserRepository,
)

__all__ = [
    "SQLAlchemyUserRepository",
]
