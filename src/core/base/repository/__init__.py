"""Repository patterns.

Provides data access abstractions:
- IRepository: Generic CRUD interface
- InMemoryRepository: Testing implementation
"""

from core.base.repository.interface import IRepository
from core.base.repository.memory import InMemoryRepository

__all__ = [
    "IRepository",
    "InMemoryRepository",
]
