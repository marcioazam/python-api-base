"""Notification service implementation.

**Feature: enterprise-features-2025, Tasks 8.2-8.8**
**Validates: Requirements 8.1, 8.4, 8.7**
"""

import logging

from core.base.patterns.result import Err, Result

from .models import (
    Notification,
    NotificationChannel,
    NotificationError,
    NotificationStatus,
    UserPreferences,
)

logger = logging.getLogger(__name__)


class NotificationService[TPayload]:
    """Service for managing notifications."""

    def __init__(self) -> None:
        self._channels: dict[str, NotificationChannel[TPayload]] = {}
        self._preferences: dict[str, UserPreferences] = {}
        self._rate_limits: dict[str, int] = {}  # user_id -> count
        self._max_per_hour: int = 100

    def register_channel(
        self, name: str, channel: NotificationChannel[TPayload]
    ) -> None:
        """Register a notification channel."""
        self._channels[name] = channel

    def set_preferences(self, preferences: UserPreferences) -> None:
        """Set user notification preferences."""
        self._preferences[preferences.user_id] = preferences

    def get_preferences(self, user_id: str) -> UserPreferences | None:
        """Get user notification preferences."""
        return self._preferences.get(user_id)

    def is_opted_out(self, user_id: str, channel: str) -> bool:
        """Check if user has opted out of a channel."""
        prefs = self._preferences.get(user_id)
        if prefs is None:
            return False

        if channel in prefs.opted_out_channels:
            return True

        if channel == "email" and not prefs.email_enabled:
            return True
        if channel == "sms" and not prefs.sms_enabled:
            return True
        if channel == "push" and not prefs.push_enabled:
            return True

        return False

    def is_rate_limited(self, user_id: str) -> bool:
        """Check if user is rate limited."""
        count = self._rate_limits.get(user_id, 0)
        return count >= self._max_per_hour

    async def send(
        self,
        notification: Notification,
        payload: TPayload,
    ) -> Result[NotificationStatus, NotificationError]:
        """Send a notification.

        Args:
            notification: The notification to send.
            payload: The payload for the channel.

        Returns:
            Result with status or error.
        """
        # Check opt-out
        if self.is_opted_out(notification.recipient_id, notification.channel):
            logger.info(
                "Notification skipped due to opt-out",
                extra={
                    "user_id": notification.recipient_id,
                    "channel": notification.channel,
                },
            )
            return Err(NotificationError.OPT_OUT)

        # Check rate limit
        if self.is_rate_limited(notification.recipient_id):
            return Err(NotificationError.RATE_LIMITED)

        # Get channel
        channel = self._channels.get(notification.channel)
        if channel is None:
            return Err(NotificationError.CHANNEL_ERROR)

        # Send
        result = await channel.send(notification.recipient_id, payload)

        # Update rate limit
        if result.is_ok():
            self._rate_limits[notification.recipient_id] = (
                self._rate_limits.get(notification.recipient_id, 0) + 1
            )

        return result

    async def send_batch(
        self,
        notifications: list[tuple[Notification, TPayload]],
    ) -> list[Result[NotificationStatus, NotificationError]]:
        """Send batch of notifications."""
        results = []
        for notification, payload in notifications:
            result = await self.send(notification, payload)
            results.append(result)
        return results
