"""Enterprise examples routes.

**Feature: enterprise-generics-2025**
**Refactored: 2025 - Split enterprise_examples_router.py (576 lines) into focused modules**
"""

from fastapi import APIRouter

from .models import (
    EmailTaskPayload,
    ExampleAction,
    ExampleResource,
    ExampleUser,
    RateLimitCheckRequest,
    RateLimitCheckResponse,
    RBACCheckRequest,
    RBACCheckResponse,
    TaskEnqueueRequest,
    TaskEnqueueResponse,
)
from .ratelimit import router as ratelimit_router
from .rbac import router as rbac_router
from .tasks import router as tasks_router
from .docs import router as docs_router

# Main enterprise router aggregating all sub-routers
router = APIRouter(prefix="/enterprise", tags=["Enterprise Examples"])

router.include_router(ratelimit_router)
router.include_router(rbac_router)
router.include_router(tasks_router)
router.include_router(docs_router)

__all__ = [
    "router",
    "EmailTaskPayload",
    "ExampleAction",
    "ExampleResource",
    "ExampleUser",
    "RateLimitCheckRequest",
    "RateLimitCheckResponse",
    "RBACCheckRequest",
    "RBACCheckResponse",
    "TaskEnqueueRequest",
    "TaskEnqueueResponse",
]
