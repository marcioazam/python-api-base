"""Dapr virtual actors.

This module provides virtual actors with state and timers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TypeVar

from core.shared.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class ActorConfig:
    """Actor configuration."""

    idle_timeout: str = "1h"
    actor_scan_interval: str = "30s"
    drain_ongoing_call_timeout: str = "60s"
    drain_rebalanced_actors: bool = True
    reentrancy_enabled: bool = False
    max_stack_depth: int | None = None


@dataclass
class ActorTimer:
    """Actor timer configuration."""

    name: str
    callback: str
    due_time: str
    period: str
    data: Any = None


@dataclass
class ActorReminder:
    """Actor reminder configuration."""

    name: str
    due_time: str
    period: str
    data: Any = None


class Actor(ABC):
    """Base class for Dapr actors."""

    def __init__(self, actor_id: str) -> None:
        """Initialize the actor.

        Args:
            actor_id: Unique actor instance ID.
        """
        self._actor_id = actor_id
        self._state_manager: "ActorStateManager | None" = None

    @property
    def id(self) -> str:
        """Get the actor ID."""
        return self._actor_id

    @property
    def state_manager(self) -> "ActorStateManager":
        """Get the actor state manager."""
        if self._state_manager is None:
            raise RuntimeError("Actor state manager not initialized")
        return self._state_manager

    def _set_state_manager(self, manager: "ActorStateManager") -> None:
        """Set the actor state manager (called by runtime)."""
        self._state_manager = manager

    @abstractmethod
    async def on_activate(self) -> None:
        """Called when actor is activated."""
        ...

    @abstractmethod
    async def on_deactivate(self) -> None:
        """Called when actor is deactivated."""
        ...

    async def get_state(self, key: str) -> Any:
        """Get actor state.

        Args:
            key: State key.

        Returns:
            State value or None.
        """
        return await self.state_manager.get_state(key)

    async def set_state(self, key: str, value: Any) -> None:
        """Set actor state.

        Args:
            key: State key.
            value: State value.
        """
        await self.state_manager.set_state(key, value)

    async def remove_state(self, key: str) -> None:
        """Remove actor state.

        Args:
            key: State key.
        """
        await self.state_manager.remove_state(key)

    async def register_timer(
        self,
        name: str,
        callback: str,
        due_time: str,
        period: str,
        data: Any = None,
    ) -> None:
        """Register a timer.

        Args:
            name: Timer name.
            callback: Callback method name.
            due_time: Time until first invocation.
            period: Interval between invocations.
            data: Data to pass to callback.
        """
        await self.state_manager.register_timer(
            ActorTimer(
                name=name,
                callback=callback,
                due_time=due_time,
                period=period,
                data=data,
            )
        )

    async def unregister_timer(self, name: str) -> None:
        """Unregister a timer.

        Args:
            name: Timer name.
        """
        await self.state_manager.unregister_timer(name)

    async def register_reminder(
        self,
        name: str,
        due_time: str,
        period: str,
        data: Any = None,
    ) -> None:
        """Register a reminder.

        Args:
            name: Reminder name.
            due_time: Time until first invocation.
            period: Interval between invocations.
            data: Data to pass to callback.
        """
        await self.state_manager.register_reminder(
            ActorReminder(
                name=name,
                due_time=due_time,
                period=period,
                data=data,
            )
        )

    async def unregister_reminder(self, name: str) -> None:
        """Unregister a reminder.

        Args:
            name: Reminder name.
        """
        await self.state_manager.unregister_reminder(name)


class ActorStateManager:
    """Manages actor state operations."""

    def __init__(
        self,
        actor_type: str,
        actor_id: str,
        http_client: Any,
        dapr_endpoint: str,
    ) -> None:
        """Initialize the actor state manager.

        Args:
            actor_type: Actor type name.
            actor_id: Actor instance ID.
            http_client: HTTP client for Dapr API calls.
            dapr_endpoint: Dapr HTTP endpoint.
        """
        self._actor_type = actor_type
        self._actor_id = actor_id
        self._http_client = http_client
        self._dapr_endpoint = dapr_endpoint

    async def get_state(self, key: str) -> Any:
        """Get actor state."""
        import json

        url = f"{self._dapr_endpoint}/v1.0/actors/{self._actor_type}/{self._actor_id}/state/{key}"
        response = await self._http_client.get(url)
        if response.status_code == 204:
            return None
        return response.json()

    async def set_state(self, key: str, value: Any) -> None:
        """Set actor state."""
        import json

        url = f"{self._dapr_endpoint}/v1.0/actors/{self._actor_type}/{self._actor_id}/state"
        await self._http_client.post(
            url,
            content=json.dumps([{"operation": "upsert", "request": {"key": key, "value": value}}]),
            headers={"Content-Type": "application/json"},
        )

    async def remove_state(self, key: str) -> None:
        """Remove actor state."""
        url = f"{self._dapr_endpoint}/v1.0/actors/{self._actor_type}/{self._actor_id}/state/{key}"
        await self._http_client.delete(url)

    async def register_timer(self, timer: ActorTimer) -> None:
        """Register an actor timer."""
        import json

        url = f"{self._dapr_endpoint}/v1.0/actors/{self._actor_type}/{self._actor_id}/timers/{timer.name}"
        await self._http_client.post(
            url,
            content=json.dumps({
                "callback": timer.callback,
                "dueTime": timer.due_time,
                "period": timer.period,
                "data": timer.data,
            }),
            headers={"Content-Type": "application/json"},
        )

    async def unregister_timer(self, name: str) -> None:
        """Unregister an actor timer."""
        url = f"{self._dapr_endpoint}/v1.0/actors/{self._actor_type}/{self._actor_id}/timers/{name}"
        await self._http_client.delete(url)

    async def register_reminder(self, reminder: ActorReminder) -> None:
        """Register an actor reminder."""
        import json

        url = f"{self._dapr_endpoint}/v1.0/actors/{self._actor_type}/{self._actor_id}/reminders/{reminder.name}"
        await self._http_client.post(
            url,
            content=json.dumps({
                "dueTime": reminder.due_time,
                "period": reminder.period,
                "data": reminder.data,
            }),
            headers={"Content-Type": "application/json"},
        )

    async def unregister_reminder(self, name: str) -> None:
        """Unregister an actor reminder."""
        url = f"{self._dapr_endpoint}/v1.0/actors/{self._actor_type}/{self._actor_id}/reminders/{name}"
        await self._http_client.delete(url)


class ActorRuntime:
    """Manages actor registration and lifecycle."""

    def __init__(self, config: ActorConfig | None = None) -> None:
        """Initialize the actor runtime.

        Args:
            config: Actor configuration.
        """
        self._config = config or ActorConfig()
        self._actor_types: dict[str, type[Actor]] = {}

    @property
    def config(self) -> ActorConfig:
        """Get actor configuration."""
        return self._config

    def register_actor(self, actor_type: type[Actor]) -> None:
        """Register an actor type.

        Args:
            actor_type: Actor class to register.
        """
        type_name = actor_type.__name__
        self._actor_types[type_name] = actor_type
        logger.info("actor_type_registered", actor_type=type_name)

    def get_registered_actors(self) -> list[str]:
        """Get list of registered actor types.

        Returns:
            List of actor type names.
        """
        return list(self._actor_types.keys())

    def get_actor_config(self) -> dict[str, Any]:
        """Get actor configuration for Dapr.

        Returns:
            Actor configuration dictionary.
        """
        config: dict[str, Any] = {
            "entities": self.get_registered_actors(),
            "actorIdleTimeout": self._config.idle_timeout,
            "actorScanInterval": self._config.actor_scan_interval,
            "drainOngoingCallTimeout": self._config.drain_ongoing_call_timeout,
            "drainRebalancedActors": self._config.drain_rebalanced_actors,
        }

        if self._config.reentrancy_enabled:
            config["reentrancy"] = {
                "enabled": True,
                "maxStackDepth": self._config.max_stack_depth,
            }

        return config
