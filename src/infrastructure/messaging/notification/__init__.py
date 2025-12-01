"""Notification service with multi-channel support and PEP 695 generics.

**Feature: enterprise-features-2025, Task 8.1**
**Validates: Requirements 8.8**
"""

from .models import (
    Notification,
    NotificationChannel,
    NotificationError,
    NotificationStatus,
    Template,
    UserPreferences,
)
from .service import NotificationService

__all__ = [
    "Notification",
    "NotificationChannel",
    "NotificationError",
    "NotificationService",
    "NotificationStatus",
    "Template",
    "UserPreferences",
]
