"""Feature routes.

Contains routes for advanced features (Kafka, Storage, Sustainability).

**Feature: interface-restructuring-2025**
"""

from interface.v1.features.kafka_router import router as kafka_router
from interface.v1.features.storage_router import router as storage_router
from interface.v1.features.sustainability_router import router as sustainability_router

__all__ = [
    "kafka_router",
    "storage_router",
    "sustainability_router",
]
