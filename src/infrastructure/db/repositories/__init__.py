"""Database repository implementations (Adapters).

**Feature: architecture-restructuring-2025**
**Validates: Requirements 6.2**
"""

from infrastructure.db.repositories.user_repository import (
    SQLAlchemyUserRepository,
)

__all__ = [
    "SQLAlchemyUserRepository",
]
