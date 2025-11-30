"""Repository implementations.

This module provides repository adapters for data persistence
using SQLModel and async SQLAlchemy.
"""

from my_api.adapters.repositories.sqlmodel_repository import SQLModelRepository

__all__ = [
    "SQLModelRepository",
]
