"""Task queue endpoints.

**Feature: enterprise-generics-2025**
"""

from typing import Any

from fastapi import APIRouter

from .dependencies import get_task_queue
from .models import EmailTaskPayload, TaskEnqueueRequest, TaskEnqueueResponse

router = APIRouter(tags=["Task Queue"])


@router.post(
    "/tasks/enqueue",
    response_model=TaskEnqueueResponse,
    summary="Enqueue Task",
)
async def enqueue_task(request: TaskEnqueueRequest) -> TaskEnqueueResponse:
    """Enqueue email task."""
    queue = await get_task_queue()

    task = EmailTaskPayload(
        to=request.to,
        subject=request.subject,
        body=request.body,
    )

    handle = await queue.enqueue(task)

    return TaskEnqueueResponse(
        task_id=handle.task_id,
        status="pending",
    )


@router.get("/tasks/{task_id}/status", summary="Get Task Status")
async def get_task_status(task_id: str) -> dict[str, Any]:
    """Get task status."""
    queue = await get_task_queue()
    status = await queue.get_status(task_id)

    return {
        "task_id": task_id,
        "status": status.value,
    }
