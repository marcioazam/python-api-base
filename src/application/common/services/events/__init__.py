"""Event services.

Provides event service implementations.

**Feature: application-layer-improvements-2025**
"""

from application.common.services.events.kafka_event_service import (
    KafkaEventService,
)

__all__ = ["KafkaEventService"]
