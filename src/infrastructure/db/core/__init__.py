"""Database core components.

Contains database session management and connection handling.

**Feature: infrastructure-restructuring-2025**
"""

from infrastructure.db.core.session import SessionLocal, get_session

__all__ = [
    "SessionLocal",
    "get_session",
]
