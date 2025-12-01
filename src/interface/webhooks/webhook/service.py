"""Webhook service with delivery and retry logic.

**Feature: enterprise-features-2025, Tasks 5.2, 5.6**
**Validates: Requirements 5.2, 5.3, 5.5, 5.7**
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from my_app.shared.result import Err, Ok, Result

from .models import (
    DeliveryError,
    DeliveryFailure,
    DeliveryResult,
    WebhookPayload,
    WebhookSubscription,
)
from .signature import generate_signature_header

logger = logging.getLogger(__name__)


@dataclass
class WebhookConfig:
    """Webhook service configuration."""

    max_retries: int = 5
    initial_retry_delay_seconds: int = 1
    max_retry_delay_seconds: int = 3600
    timeout_seconds: int = 30
    backoff_multiplier: float = 2.0


@dataclass
class DeliveryStats:
    """Delivery statistics for a webhook."""

    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    total_retries: int = 0
    average_response_time_ms: float = 0.0


class WebhookService[TEvent]:
    """Service for managing webhook subscriptions and deliveries.

    Type Parameters:
        TEvent: The type of events this service handles.
    """

    def __init__(self, config: WebhookConfig | None = None) -> None:
        """Initialize webhook service."""
        self._config = config or WebhookConfig()
        self._subscriptions: dict[str, WebhookSubscription] = {}
        self._stats: dict[str, DeliveryStats] = {}
        self._retry_queue: list[tuple[WebhookPayload[TEvent], WebhookSubscription, int]] = []

    def register(self, subscription: WebhookSubscription) -> None:
        """Register a webhook subscription.

        Args:
            subscription: The subscription to register.
        """
        self._subscriptions[subscription.id] = subscription
        self._stats[subscription.id] = DeliveryStats()
        logger.info(f"Registered webhook {subscription.id} for events {subscription.events}")

    def unregister(self, webhook_id: str) -> bool:
        """Unregister a webhook subscription.

        Args:
            webhook_id: The subscription ID to remove.

        Returns:
            True if subscription was removed.
        """
        if webhook_id in self._subscriptions:
            del self._subscriptions[webhook_id]
            del self._stats[webhook_id]
            return True
        return False

    def get_subscription(self, webhook_id: str) -> WebhookSubscription | None:
        """Get a webhook subscription by ID."""
        return self._subscriptions.get(webhook_id)

    def list_subscriptions(self, event_type: str | None = None) -> list[WebhookSubscription]:
        """List all subscriptions, optionally filtered by event type."""
        subs = list(self._subscriptions.values())
        if event_type:
            subs = [s for s in subs if event_type in s.events]
        return subs

    def get_stats(self, webhook_id: str) -> DeliveryStats | None:
        """Get delivery statistics for a webhook."""
        return self._stats.get(webhook_id)

    def calculate_retry_delay(self, attempt: int) -> int:
        """Calculate retry delay using exponential backoff.

        Args:
            attempt: The current attempt number (1-based).

        Returns:
            Delay in seconds before next retry.
        """
        delay = self._config.initial_retry_delay_seconds * (
            self._config.backoff_multiplier ** (attempt - 1)
        )
        return min(int(delay), self._config.max_retry_delay_seconds)

    async def deliver(
        self,
        payload: WebhookPayload[TEvent],
        subscription: WebhookSubscription,
    ) -> Result[DeliveryResult, DeliveryFailure]:
        """Deliver a webhook payload to a subscription.

        Args:
            payload: The payload to deliver.
            subscription: The target subscription.

        Returns:
            Result with DeliveryResult on success or DeliveryFailure on error.
        """
        if not subscription.is_active:
            return Err(
                DeliveryFailure(
                    webhook_id=subscription.id,
                    event_id=payload.event_id,
                    error=DeliveryError.INVALID_URL,
                    error_message="Webhook subscription is inactive",
                    attempt=payload.attempt,
                )
            )

        # Prepare payload dict
        payload_dict = {
            "event_type": payload.event_type,
            "event_id": payload.event_id,
            "timestamp": payload.timestamp.isoformat(),
            "data": payload.data if isinstance(payload.data, dict) else str(payload.data),
        }

        # Generate signature headers
        headers = generate_signature_header(payload_dict, subscription.secret)
        headers["Content-Type"] = "application/json"

        start_time = time.monotonic()

        try:
            import httpx

            async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
                response = await client.post(
                    subscription.url,
                    json=payload_dict,
                    headers=headers,
                )

            response_time_ms = int((time.monotonic() - start_time) * 1000)

            # Update stats
            stats = self._stats.get(subscription.id)
            if stats:
                stats.total_deliveries += 1
                if 200 <= response.status_code < 300:
                    stats.successful_deliveries += 1
                else:
                    stats.failed_deliveries += 1

            if 200 <= response.status_code < 300:
                return Ok(
                    DeliveryResult(
                        webhook_id=subscription.id,
                        event_id=payload.event_id,
                        status_code=response.status_code,
                        response_time_ms=response_time_ms,
                        delivered_at=datetime.now(UTC),
                        attempt=payload.attempt,
                    )
                )
            return Err(
                DeliveryFailure(
                    webhook_id=subscription.id,
                    event_id=payload.event_id,
                    error=DeliveryError.INVALID_RESPONSE,
                    error_message=f"HTTP {response.status_code}",
                    attempt=payload.attempt,
                    next_retry_at=self._calculate_next_retry(payload.attempt),
                )
            )

        except TimeoutError:
            return Err(
                DeliveryFailure(
                    webhook_id=subscription.id,
                    event_id=payload.event_id,
                    error=DeliveryError.TIMEOUT,
                    error_message=f"Timeout after {self._config.timeout_seconds}s",
                    attempt=payload.attempt,
                    next_retry_at=self._calculate_next_retry(payload.attempt),
                )
            )
        except Exception as e:
            return Err(
                DeliveryFailure(
                    webhook_id=subscription.id,
                    event_id=payload.event_id,
                    error=DeliveryError.CONNECTION_ERROR,
                    error_message=str(e),
                    attempt=payload.attempt,
                    next_retry_at=self._calculate_next_retry(payload.attempt),
                )
            )

    def _calculate_next_retry(self, current_attempt: int) -> datetime | None:
        """Calculate next retry time."""
        if current_attempt >= self._config.max_retries:
            return None
        delay = self.calculate_retry_delay(current_attempt + 1)
        return datetime.now(UTC) + timedelta(seconds=delay)

    async def deliver_with_retry(
        self,
        payload: WebhookPayload[TEvent],
        subscription: WebhookSubscription,
    ) -> Result[DeliveryResult, DeliveryFailure]:
        """Deliver with automatic retry on failure.

        Args:
            payload: The payload to deliver.
            subscription: The target subscription.

        Returns:
            Final result after all retry attempts.
        """
        current_payload = payload
        stats = self._stats.get(subscription.id)

        for attempt in range(1, self._config.max_retries + 1):
            current_payload = WebhookPayload(
                event_type=payload.event_type,
                event_id=payload.event_id,
                timestamp=payload.timestamp,
                data=payload.data,
                webhook_id=subscription.id,
                attempt=attempt,
            )

            result = await self.deliver(current_payload, subscription)

            if result.is_ok():
                return result

            # Log retry
            if stats:
                stats.total_retries += 1

            if attempt < self._config.max_retries:
                delay = self.calculate_retry_delay(attempt)
                logger.info(
                    f"Webhook delivery failed, retrying in {delay}s",
                    extra={"webhook_id": subscription.id, "attempt": attempt},
                )
                await asyncio.sleep(delay)

        # All retries exhausted
        return Err(
            DeliveryFailure(
                webhook_id=subscription.id,
                event_id=payload.event_id,
                error=DeliveryError.MAX_RETRIES_EXCEEDED,
                error_message=f"Failed after {self._config.max_retries} attempts",
                attempt=self._config.max_retries,
            )
        )

    async def broadcast(
        self,
        event_type: str,
        event_id: str,
        data: TEvent,
    ) -> dict[str, Result[DeliveryResult, DeliveryFailure]]:
        """Broadcast an event to all subscribed webhooks.

        Args:
            event_type: The type of event.
            event_id: Unique event identifier.
            data: The event data.

        Returns:
            Dictionary mapping webhook IDs to delivery results.
        """
        payload = WebhookPayload(
            event_type=event_type,
            event_id=event_id,
            timestamp=datetime.now(UTC),
            data=data,
        )

        results: dict[str, Result[DeliveryResult, DeliveryFailure]] = {}
        subscriptions = self.list_subscriptions(event_type)

        for subscription in subscriptions:
            if subscription.is_active:
                results[subscription.id] = await self.deliver_with_retry(
                    payload, subscription
                )

        return results
