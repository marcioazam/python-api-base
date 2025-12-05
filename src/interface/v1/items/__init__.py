"""Items API routes.

Contains routes for item management.

**Feature: interface-restructuring-2025**
"""

from interface.v1.items.items_router import router as items_router

__all__ = [
    "items_router",
]
