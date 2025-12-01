"""Webhook outbound delivery with HMAC signing.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 5.3**
"""

import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any
from collections.abc import Callable

import httpx

from my_app.shared.utils.ids import generate_ulid

logger = logging.getLogger(__name__)


class WebhookStatus(str, Enum):
    """Webhook delivery status."""
    
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass(frozen=True, slots=True)
class WebhookConfig:
    """Webhook endpoint configuration.
    
    Attributes:
        url: Target URL for webhook delivery.
        secret: HMAC secret for signing payloads.
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts.
        retry_delay: Base delay between retries in seconds.
    """
    
    url: str
    secret: str
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class WebhookDeliveryResult:
    """Result of webhook delivery attempt.
    
    Attributes:
        id: Unique delivery ID.
        status: Delivery status.
        status_code: HTTP status code (if delivered).
        attempts: Number of delivery attempts.
        error: Error message (if failed).
        delivered_at: Timestamp of successful delivery.
    """
    
    id: str
    status: WebhookStatus
    status_code: int | None = None
    attempts: int = 0
    error: str | None = None
    delivered_at: datetime | None = None


def generate_signature(payload: bytes, secret: str, timestamp: int) -> str:
    """Generate HMAC-SHA256 signature for webhook payload.
    
    **Feature: architecture-restructuring-2025**
    **Validates: Requirements 5.3**
    
    Args:
        payload: Raw payload bytes.
        secret: HMAC secret key.
        timestamp: Unix timestamp for replay protection.
        
    Returns:
        Hex-encoded HMAC signature.
    """
    message = f"{timestamp}.{payload.decode('utf-8')}"
    signature = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature


def verify_signature(
    payload: bytes,
    secret: str,
    signature: str,
    timestamp: int,
    tolerance: int = 300,
) -> bool:
    """Verify HMAC-SHA256 signature of webhook payload.
    
    Args:
        payload: Raw payload bytes.
        secret: HMAC secret key.
        signature: Signature to verify.
        timestamp: Unix timestamp from request.
        tolerance: Maximum age of signature in seconds.
        
    Returns:
        True if signature is valid and not expired.
    """
    # Check timestamp tolerance
    current_time = int(time.time())
    if abs(current_time - timestamp) > tolerance:
        logger.warning(
            "Webhook signature expired",
            extra={"timestamp": timestamp, "current": current_time},
        )
        return False
    
    expected = generate_signature(payload, secret, timestamp)
    return hmac.compare_digest(signature, expected)


class WebhookDeliveryService:
    """Service for delivering webhooks with HMAC signing.
    
    **Feature: architecture-restructuring-2025**
    **Validates: Requirements 5.3**
    """
    
    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize webhook delivery service.
        
        Args:
            http_client: Optional HTTP client for testing.
        """
        self._client = http_client
        self._own_client = http_client is None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client if owned."""
        if self._own_client and self._client is not None:
            await self._client.aclose()
            self._client = None
    
    def _build_headers(
        self,
        payload: bytes,
        config: WebhookConfig,
        event_type: str,
    ) -> dict[str, str]:
        """Build webhook request headers with signature.
        
        Args:
            payload: Raw payload bytes.
            config: Webhook configuration.
            event_type: Type of webhook event.
            
        Returns:
            Headers dictionary.
        """
        timestamp = int(time.time())
        signature = generate_signature(payload, config.secret, timestamp)
        
        return {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Timestamp": str(timestamp),
            "X-Webhook-Event": event_type,
            "X-Webhook-ID": generate_ulid(),
        }
    
    async def deliver(
        self,
        config: WebhookConfig,
        event_type: str,
        payload: dict[str, Any],
    ) -> WebhookDeliveryResult:
        """Deliver webhook with retries.
        
        **Feature: architecture-restructuring-2025**
        **Validates: Requirements 5.3**
        
        Args:
            config: Webhook endpoint configuration.
            event_type: Type of webhook event.
            payload: Payload to deliver.
            
        Returns:
            Delivery result with status and metadata.
        """
        delivery_id = generate_ulid()
        payload_bytes = json.dumps(payload).encode("utf-8")
        headers = self._build_headers(payload_bytes, config, event_type)
        
        client = await self._get_client()
        last_error: str | None = None
        
        for attempt in range(1, config.max_retries + 1):
            try:
                response = await client.post(
                    config.url,
                    content=payload_bytes,
                    headers=headers,
                    timeout=config.timeout,
                )
                
                if 200 <= response.status_code < 300:
                    logger.info(
                        f"Webhook delivered successfully",
                        extra={
                            "delivery_id": delivery_id,
                            "url": config.url,
                            "event_type": event_type,
                            "status_code": response.status_code,
                            "attempts": attempt,
                        },
                    )
                    return WebhookDeliveryResult(
                        id=delivery_id,
                        status=WebhookStatus.DELIVERED,
                        status_code=response.status_code,
                        attempts=attempt,
                        delivered_at=datetime.now(UTC),
                    )
                
                last_error = f"HTTP {response.status_code}"
                logger.warning(
                    f"Webhook delivery failed with status {response.status_code}",
                    extra={
                        "delivery_id": delivery_id,
                        "attempt": attempt,
                        "status_code": response.status_code,
                    },
                )
                
            except httpx.TimeoutException as e:
                last_error = f"Timeout: {e}"
                logger.warning(
                    f"Webhook delivery timeout",
                    extra={"delivery_id": delivery_id, "attempt": attempt},
                )
                
            except httpx.RequestError as e:
                last_error = f"Request error: {e}"
                logger.warning(
                    f"Webhook delivery error: {e}",
                    extra={"delivery_id": delivery_id, "attempt": attempt},
                )
            
            # Wait before retry (exponential backoff)
            if attempt < config.max_retries:
                delay = config.retry_delay * (2 ** (attempt - 1))
                await self._sleep(delay)
        
        logger.error(
            f"Webhook delivery failed after {config.max_retries} attempts",
            extra={
                "delivery_id": delivery_id,
                "url": config.url,
                "event_type": event_type,
                "error": last_error,
            },
        )
        
        return WebhookDeliveryResult(
            id=delivery_id,
            status=WebhookStatus.FAILED,
            attempts=config.max_retries,
            error=last_error,
        )
    
    async def _sleep(self, seconds: float) -> None:
        """Sleep for retry delay (can be mocked in tests)."""
        import asyncio
        await asyncio.sleep(seconds)


# Convenience function for one-off deliveries
async def deliver_webhook(
    url: str,
    secret: str,
    event_type: str,
    payload: dict[str, Any],
    timeout: float = 30.0,
    max_retries: int = 3,
) -> WebhookDeliveryResult:
    """Deliver a webhook to a URL.
    
    Args:
        url: Target URL.
        secret: HMAC secret for signing.
        event_type: Type of webhook event.
        payload: Payload to deliver.
        timeout: Request timeout.
        max_retries: Maximum retry attempts.
        
    Returns:
        Delivery result.
    """
    config = WebhookConfig(
        url=url,
        secret=secret,
        timeout=timeout,
        max_retries=max_retries,
    )
    
    service = WebhookDeliveryService()
    try:
        return await service.deliver(config, event_type, payload)
    finally:
        await service.close()
