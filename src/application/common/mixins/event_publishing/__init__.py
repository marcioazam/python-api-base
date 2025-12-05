"""Event publishing mixin for domain entities.

Provides mixin for entities that publish domain events.

**Feature: application-layer-improvements-2025**
"""

from application.common.mixins.event_publishing.event_publishing import (
    EventPublishingMixin,
)

__all__ = ["EventPublishingMixin"]
