"""Kafka messaging endpoints.

Demonstrates Kafka producer usage for publishing messages.

**Feature: kafka-workflow-integration**
**Refactored: Split from infrastructure_router.py for SRP compliance**
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kafka", tags=["Kafka"])


# =============================================================================
# DTOs
# =============================================================================


class KafkaPublishRequest(BaseModel):
    """Request to publish Kafka message."""

    topic: str = Field(default="test-events", min_length=1, max_length=256)
    key: str | None = Field(default=None, max_length=256)
    payload: dict[str, Any] = Field(..., examples=[{"event": "test", "data": "hello"}])
    headers: dict[str, str] | None = Field(default=None)


class KafkaPublishResponse(BaseModel):
    """Kafka publish response."""

    topic: str
    partition: int
    offset: int
    timestamp: str


class KafkaStatusResponse(BaseModel):
    """Kafka status response."""

    enabled: bool
    connected: bool
    client_id: str | None = None
    bootstrap_servers: list[str] | None = None


# =============================================================================
# Dependencies
# =============================================================================


def get_kafka(request: Request) -> Any:
    """Get Kafka producer from app state.

    **Feature: kafka-workflow-integration**
    **Validates: Requirements 2.3**

    Returns:
        Kafka producer instance.

    Raises:
        HTTPException: 503 if Kafka not configured.
    """
    producer = getattr(request.app.state, "kafka_producer", None)
    if producer is None:
        raise HTTPException(
            status_code=503,
            detail="Kafka not configured. Set OBSERVABILITY__KAFKA_ENABLED=true",
        )
    return producer


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/publish",
    response_model=KafkaPublishResponse,
    summary="Publish Kafka message",
    description="Publish a test message to Kafka topic",
)
async def kafka_publish(
    request: KafkaPublishRequest,
    producer=Depends(get_kafka),
) -> KafkaPublishResponse:
    """Publish test message to Kafka.

    **Requirement: R2.1 - Publish test message**
    **Requirement: R2.4 - Return message metadata**
    """
    try:
        metadata = await producer.send(
            payload=request.payload,
            key=request.key,
            headers=request.headers,
            topic=request.topic,
        )

        return KafkaPublishResponse(
            topic=metadata.topic,
            partition=metadata.partition,
            offset=metadata.offset,
            timestamp=metadata.timestamp.isoformat() if metadata.timestamp else "",
        )
    except Exception as e:
        logger.error("Kafka publish failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Kafka publish failed: {e}") from e


@router.get(
    "/status",
    response_model=KafkaStatusResponse,
    summary="Kafka status",
    description="Get Kafka producer connection status",
)
async def kafka_status(request: Request) -> KafkaStatusResponse:
    """Get Kafka producer status.

    **Requirement: R2.2 - Return producer status**
    """
    producer = getattr(request.app.state, "kafka_producer", None)
    settings = request.app.state.settings.observability

    return KafkaStatusResponse(
        enabled=settings.kafka_enabled,
        connected=producer is not None and producer._started,
        client_id=settings.kafka_client_id if settings.kafka_enabled else None,
        bootstrap_servers=settings.kafka_bootstrap_servers
        if settings.kafka_enabled
        else None,
    )
