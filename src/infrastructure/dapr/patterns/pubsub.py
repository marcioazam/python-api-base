"""Dapr pub/sub messaging.

This module provides publish/subscribe messaging with CloudEvents support.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

from pydantic import BaseModel

from core.shared.logging import get_logger
from infrastructure.dapr.client import DaprClientWrapper
from infrastructure.dapr.errors import DaprConnectionError

logger = get_logger(__name__)


class CloudEvent(BaseModel):
    """CloudEvents 1.0 specification model."""

    specversion: str = "1.0"
    type: str
    source: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    time: str | None = None
    datacontenttype: str = "application/json"
    data: Any
    traceparent: str | None = None
    tracestate: str | None = None
    pubsubname: str | None = None
    topic: str | None = None

    model_config = {"extra": "allow"}


class MessageStatus(Enum):
    """Pub/sub message processing status."""

    SUCCESS = "SUCCESS"
    RETRY = "RETRY"
    DROP = "DROP"


@dataclass
class Subscription:
    """Pub/sub subscription configuration."""

    pubsub_name: str
    topic: str
    route: str
    dead_letter_topic: str | None = None
    metadata: dict[str, str] | None = None
    bulk_subscribe: bool = False
    max_messages_count: int | None = None
    max_await_duration_ms: int | None = None


@dataclass
class PublishOptions:
    """Options for publishing messages."""

    content_type: str = "application/json"
    metadata: dict[str, str] | None = None
    raw_payload: bool = False


class PubSubManager:
    """Manages pub/sub operations."""

    def __init__(self, client: DaprClientWrapper, pubsub_name: str) -> None:
        """Initialize the pub/sub manager.

        Args:
            client: Dapr client wrapper.
            pubsub_name: Default pub/sub component name.
        """
        self._client = client
        self._pubsub_name = pubsub_name
        self._subscriptions: list[Subscription] = []
        self._handlers: dict[str, Callable[[CloudEvent], Awaitable[MessageStatus]]] = (
            {}
        )

    @property
    def pubsub_name(self) -> str:
        """Get the default pub/sub name."""
        return self._pubsub_name

    async def publish(
        self,
        topic: str,
        data: Any,
        pubsub_name: str | None = None,
        options: PublishOptions | None = None,
    ) -> None:
        """Publish a message to a topic.

        Args:
            topic: Topic name.
            data: Message data.
            pubsub_name: Pub/sub component name (uses default if not specified).
            options: Publish options.
        """
        pubsub = pubsub_name or self._pubsub_name
        opts = options or PublishOptions()

        content: bytes
        if isinstance(data, bytes):
            content = data
        elif isinstance(data, str):
            content = data.encode()
        else:
            content = json.dumps(data).encode()

        metadata = opts.metadata or {}
        if opts.raw_payload:
            metadata["rawPayload"] = "true"

        await self._client.publish_event(
            pubsub_name=pubsub,
            topic_name=topic,
            data=content,
            data_content_type=opts.content_type,
            metadata=metadata if metadata else None,
        )

        logger.debug(
            "message_published",
            pubsub=pubsub,
            topic=topic,
            content_type=opts.content_type,
        )

    async def publish_bulk(
        self,
        topic: str,
        messages: list[Any],
        pubsub_name: str | None = None,
        options: PublishOptions | None = None,
    ) -> None:
        """Publish multiple messages in a batch.

        Args:
            topic: Topic name.
            messages: List of message data.
            pubsub_name: Pub/sub component name.
            options: Publish options.
        """
        pubsub = pubsub_name or self._pubsub_name
        opts = options or PublishOptions()

        url = f"/v1.0-alpha1/publish/bulk/{pubsub}/{topic}"
        headers = {"Content-Type": "application/json"}

        entries = []
        for i, msg in enumerate(messages):
            entry = {
                "entryId": str(i),
                "event": msg if isinstance(msg, dict) else {"data": msg},
                "contentType": opts.content_type,
            }
            if opts.metadata:
                entry["metadata"] = opts.metadata
            entries.append(entry)

        try:
            response = await self._client.http_client.post(
                url,
                content=json.dumps(entries),
                headers=headers,
            )
            response.raise_for_status()
            logger.debug(
                "bulk_messages_published",
                pubsub=pubsub,
                topic=topic,
                count=len(messages),
            )
        except Exception as e:
            raise DaprConnectionError(
                message=f"Failed to bulk publish to {pubsub}/{topic}",
                details={"error": str(e)},
            ) from e

    def subscribe(
        self,
        topic: str,
        handler: Callable[[CloudEvent], Awaitable[MessageStatus]],
        pubsub_name: str | None = None,
        route: str | None = None,
        dead_letter_topic: str | None = None,
    ) -> None:
        """Register a subscription handler.

        Args:
            topic: Topic name.
            handler: Async handler function.
            pubsub_name: Pub/sub component name.
            route: HTTP route for the subscription.
            dead_letter_topic: Dead letter topic for failed messages.
        """
        pubsub = pubsub_name or self._pubsub_name
        subscription_route = route or f"/dapr/subscribe/{pubsub}/{topic}"

        subscription = Subscription(
            pubsub_name=pubsub,
            topic=topic,
            route=subscription_route,
            dead_letter_topic=dead_letter_topic,
        )
        self._subscriptions.append(subscription)
        self._handlers[f"{pubsub}:{topic}"] = handler

        logger.info(
            "subscription_registered",
            pubsub=pubsub,
            topic=topic,
            route=subscription_route,
        )

    def get_subscriptions(self) -> list[dict[str, Any]]:
        """Get all registered subscriptions for Dapr.

        Returns:
            List of subscription configurations for Dapr.
        """
        result = []
        for sub in self._subscriptions:
            subscription: dict[str, Any] = {
                "pubsubname": sub.pubsub_name,
                "topic": sub.topic,
                "route": sub.route,
            }
            if sub.dead_letter_topic:
                subscription["deadLetterTopic"] = sub.dead_letter_topic
            if sub.metadata:
                subscription["metadata"] = sub.metadata
            if sub.bulk_subscribe:
                subscription["bulkSubscribe"] = {
                    "enabled": True,
                    "maxMessagesCount": sub.max_messages_count or 100,
                    "maxAwaitDurationMs": sub.max_await_duration_ms or 1000,
                }
            result.append(subscription)
        return result

    async def handle_message(
        self,
        pubsub_name: str,
        topic: str,
        event: CloudEvent,
    ) -> MessageStatus:
        """Handle an incoming message.

        Args:
            pubsub_name: Pub/sub component name.
            topic: Topic name.
            event: CloudEvent message.

        Returns:
            Message processing status.
        """
        handler_key = f"{pubsub_name}:{topic}"
        handler = self._handlers.get(handler_key)

        if not handler:
            logger.warning(
                "no_handler_for_message",
                pubsub=pubsub_name,
                topic=topic,
            )
            return MessageStatus.DROP

        try:
            return await handler(event)
        except Exception as e:
            logger.error(
                "message_handler_error",
                pubsub=pubsub_name,
                topic=topic,
                error=str(e),
            )
            return MessageStatus.RETRY
