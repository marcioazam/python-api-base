"""Database repository implementations (Adapters).

**Feature: architecture-restructuring-2025**
**Validates: Requirements 6.2**

Provides:
- SQLModelRepository: Generic repository for SQLModel/FastAPI projects
- SQLAlchemyUserRepository: Concrete user repository implementation
"""

from infrastructure.db.repositories.sqlmodel_repository import (
    SQLModelRepository,
)
from infrastructure.db.repositories.user_repository import (
    SQLAlchemyUserRepository,
)

__all__ = [
    # Generic repository
    "SQLModelRepository",
    # Concrete implementations
    "SQLAlchemyUserRepository",
]
