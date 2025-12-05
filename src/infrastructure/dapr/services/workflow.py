"""Dapr workflow engine.

This module provides workflow orchestration with activities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar
import uuid

from core.shared.logging import get_logger
from infrastructure.dapr.client import DaprClientWrapper
from infrastructure.dapr.errors import DaprConnectionError, WorkflowError

logger = get_logger(__name__)

T = TypeVar("T")


class WorkflowStatus(Enum):
    """Workflow execution status."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"
    SUSPENDED = "SUSPENDED"


@dataclass
class WorkflowState:
    """Workflow instance state."""

    instance_id: str
    workflow_name: str
    status: WorkflowStatus
    created_at: str
    last_updated_at: str
    input: Any | None = None
    output: Any | None = None
    error: str | None = None


class WorkflowActivity(ABC):
    """Base class for workflow activities."""

    @abstractmethod
    async def run(self, input: Any) -> Any:
        """Execute the activity.

        Args:
            input: Activity input.

        Returns:
            Activity output.
        """
        ...


class Workflow(ABC):
    """Base class for workflows."""

    @abstractmethod
    async def run(self, ctx: "WorkflowContext", input: Any) -> Any:
        """Execute the workflow.

        Args:
            ctx: Workflow context.
            input: Workflow input.

        Returns:
            Workflow output.
        """
        ...


class WorkflowContext:
    """Context for workflow execution."""

    def __init__(
        self,
        instance_id: str,
        client: DaprClientWrapper,
    ) -> None:
        """Initialize the workflow context.

        Args:
            instance_id: Workflow instance ID.
            client: Dapr client wrapper.
        """
        self._instance_id = instance_id
        self._client = client

    @property
    def instance_id(self) -> str:
        """Get the workflow instance ID."""
        return self._instance_id

    async def call_activity(
        self,
        activity: type[WorkflowActivity],
        input: Any = None,
        retry_policy: dict[str, Any] | None = None,
    ) -> Any:
        """Call an activity.

        Args:
            activity: Activity class.
            input: Activity input.
            retry_policy: Retry policy configuration.

        Returns:
            Activity output.
        """
        activity_instance = activity()
        return await activity_instance.run(input)

    async def call_child_workflow(
        self,
        workflow: type[Workflow],
        input: Any = None,
        instance_id: str | None = None,
    ) -> Any:
        """Call a child workflow.

        Args:
            workflow: Workflow class.
            input: Workflow input.
            instance_id: Optional instance ID.

        Returns:
            Workflow output.
        """
        child_id = instance_id or str(uuid.uuid4())
        workflow_instance = workflow()
        child_ctx = WorkflowContext(child_id, self._client)
        return await workflow_instance.run(child_ctx, input)

    async def create_timer(self, fire_at: str) -> None:
        """Create a durable timer.

        Args:
            fire_at: ISO 8601 timestamp when timer should fire.
        """
        import asyncio
        from datetime import datetime

        target = datetime.fromisoformat(fire_at.replace("Z", "+00:00"))
        now = datetime.now(target.tzinfo)
        delay = (target - now).total_seconds()

        if delay > 0:
            await asyncio.sleep(delay)

    async def wait_for_external_event(
        self,
        event_name: str,
        timeout: str | None = None,
    ) -> Any:
        """Wait for an external event.

        Args:
            event_name: Event name to wait for.
            timeout: Optional timeout duration.

        Returns:
            Event data.
        """
        raise NotImplementedError("External events require Dapr workflow runtime")


class WorkflowEngine:
    """Manages workflow execution."""

    def __init__(self, client: DaprClientWrapper) -> None:
        """Initialize the workflow engine.

        Args:
            client: Dapr client wrapper.
        """
        self._client = client
        self._workflows: dict[str, type[Workflow]] = {}
        self._activities: dict[str, type[WorkflowActivity]] = {}

    def register_workflow(self, workflow: type[Workflow]) -> None:
        """Register a workflow.

        Args:
            workflow: Workflow class to register.
        """
        name = workflow.__name__
        self._workflows[name] = workflow
        logger.info("workflow_registered", workflow=name)

    def register_activity(self, activity: type[WorkflowActivity]) -> None:
        """Register an activity.

        Args:
            activity: Activity class to register.
        """
        name = activity.__name__
        self._activities[name] = activity
        logger.info("activity_registered", activity=name)

    async def start_workflow(
        self,
        workflow_name: str,
        input: Any = None,
        instance_id: str | None = None,
    ) -> str:
        """Start a workflow instance.

        Args:
            workflow_name: Workflow name.
            input: Workflow input.
            instance_id: Optional instance ID.

        Returns:
            Workflow instance ID.
        """
        import json

        instance = instance_id or str(uuid.uuid4())
        url = f"/v1.0-beta1/workflows/dapr/{workflow_name}/start?instanceID={instance}"

        try:
            response = await self._client.http_client.post(
                url,
                content=json.dumps(input) if input else None,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            logger.info(
                "workflow_started",
                workflow=workflow_name,
                instance_id=instance,
            )

            return instance
        except Exception as e:
            raise WorkflowError(
                message=f"Failed to start workflow {workflow_name}",
                workflow_name=workflow_name,
                instance_id=instance,
                details={"error": str(e)},
            ) from e

    async def get_workflow_state(self, instance_id: str) -> WorkflowState:
        """Get workflow state.

        Args:
            instance_id: Workflow instance ID.

        Returns:
            WorkflowState with current status.
        """
        url = f"/v1.0-beta1/workflows/dapr/{instance_id}"

        try:
            response = await self._client.http_client.get(url)
            response.raise_for_status()
            data = response.json()

            return WorkflowState(
                instance_id=data.get("instanceID", instance_id),
                workflow_name=data.get("workflowName", ""),
                status=WorkflowStatus(data.get("runtimeStatus", "PENDING")),
                created_at=data.get("createdAt", ""),
                last_updated_at=data.get("lastUpdatedAt", ""),
                input=data.get("input"),
                output=data.get("output"),
                error=data.get("failureDetails", {}).get("message"),
            )
        except Exception as e:
            raise WorkflowError(
                message=f"Failed to get workflow state",
                instance_id=instance_id,
                details={"error": str(e)},
            ) from e

    async def terminate_workflow(
        self,
        instance_id: str,
        reason: str | None = None,
    ) -> None:
        """Terminate a workflow.

        Args:
            instance_id: Workflow instance ID.
            reason: Termination reason.
        """
        url = f"/v1.0-beta1/workflows/dapr/{instance_id}/terminate"

        try:
            response = await self._client.http_client.post(url)
            response.raise_for_status()

            logger.info(
                "workflow_terminated",
                instance_id=instance_id,
                reason=reason,
            )
        except Exception as e:
            raise WorkflowError(
                message=f"Failed to terminate workflow",
                instance_id=instance_id,
                details={"error": str(e)},
            ) from e

    async def raise_event(
        self,
        instance_id: str,
        event_name: str,
        data: Any = None,
    ) -> None:
        """Raise an event to a workflow.

        Args:
            instance_id: Workflow instance ID.
            event_name: Event name.
            data: Event data.
        """
        import json

        url = f"/v1.0-beta1/workflows/dapr/{instance_id}/raiseEvent/{event_name}"

        try:
            response = await self._client.http_client.post(
                url,
                content=json.dumps(data) if data else None,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            logger.info(
                "workflow_event_raised",
                instance_id=instance_id,
                event_name=event_name,
            )
        except Exception as e:
            raise WorkflowError(
                message=f"Failed to raise event {event_name}",
                instance_id=instance_id,
                details={"error": str(e)},
            ) from e

    async def pause_workflow(self, instance_id: str) -> None:
        """Pause a workflow.

        Args:
            instance_id: Workflow instance ID.
        """
        url = f"/v1.0-beta1/workflows/dapr/{instance_id}/pause"

        try:
            response = await self._client.http_client.post(url)
            response.raise_for_status()
            logger.info("workflow_paused", instance_id=instance_id)
        except Exception as e:
            raise WorkflowError(
                message="Failed to pause workflow",
                instance_id=instance_id,
                details={"error": str(e)},
            ) from e

    async def resume_workflow(self, instance_id: str) -> None:
        """Resume a paused workflow.

        Args:
            instance_id: Workflow instance ID.
        """
        url = f"/v1.0-beta1/workflows/dapr/{instance_id}/resume"

        try:
            response = await self._client.http_client.post(url)
            response.raise_for_status()
            logger.info("workflow_resumed", instance_id=instance_id)
        except Exception as e:
            raise WorkflowError(
                message="Failed to resume workflow",
                instance_id=instance_id,
                details={"error": str(e)},
            ) from e
