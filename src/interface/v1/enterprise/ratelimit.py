"""Rate limiter endpoints.

**Feature: enterprise-generics-2025**
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter

from infrastructure.ratelimit import RateLimit

from .dependencies import get_rate_limiter
from .models import RateLimitCheckRequest, RateLimitCheckResponse

router = APIRouter(tags=["Rate Limiter"])


@router.post(
    "/ratelimit/check",
    response_model=RateLimitCheckResponse,
    summary="Check Rate Limit",
)
async def check_rate_limit(request: RateLimitCheckRequest) -> RateLimitCheckResponse:
    """Check rate limit for client."""
    limiter = get_rate_limiter()
    limit = RateLimit(requests=10, window=timedelta(minutes=1))
    result = await limiter.check(request.client_id, limit)

    return RateLimitCheckResponse(
        client_id=request.client_id,
        is_allowed=result.is_allowed,
        remaining=result.remaining,
        limit=result.limit,
        reset_at=result.reset_at.isoformat(),
    )


@router.post("/ratelimit/reset/{client_id}", summary="Reset Rate Limit")
async def reset_rate_limit(client_id: str) -> dict[str, Any]:
    """Reset rate limit for client."""
    limiter = get_rate_limiter()
    success = await limiter.reset(client_id)
    return {"client_id": client_id, "reset": success}
