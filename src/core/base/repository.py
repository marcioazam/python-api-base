"""Compatibility alias for core.base.repository.

Use core.base.repository directly for new code.
"""

from core.base.repository import IRepository, InMemoryRepository

__all__ = ["IRepository", "InMemoryRepository"]
