"""Dapr-specific error types.

This module defines custom exceptions for Dapr operations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DaprError(Exception):
    """Base exception for Dapr operations."""

    message: str
    error_code: str = "DAPR_ERROR"
    details: dict[str, Any] | None = None
    trace_id: str | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


@dataclass
class DaprConnectionError(DaprError):
    """Raised when Dapr sidecar is unavailable."""

    error_code: str = "DAPR_CONNECTION_ERROR"
    endpoint: str | None = None

    def __str__(self) -> str:
        if self.endpoint:
            return f"[{self.error_code}] {self.message} (endpoint: {self.endpoint})"
        return super().__str__()


@dataclass
class DaprTimeoutError(DaprError):
    """Raised when a Dapr operation times out."""

    error_code: str = "DAPR_TIMEOUT_ERROR"
    timeout_seconds: float | None = None
    operation: str | None = None

    def __str__(self) -> str:
        parts = [f"[{self.error_code}] {self.message}"]
        if self.operation:
            parts.append(f"operation: {self.operation}")
        if self.timeout_seconds:
            parts.append(f"timeout: {self.timeout_seconds}s")
        return " ".join(parts)


@dataclass
class StateNotFoundError(DaprError):
    """Raised when a state key is not found."""

    error_code: str = "STATE_NOT_FOUND"
    store_name: str | None = None
    key: str | None = None

    def __str__(self) -> str:
        if self.store_name and self.key:
            return f"[{self.error_code}] State key '{self.key}' not found in store '{self.store_name}'"
        return super().__str__()


@dataclass
class SecretNotFoundError(DaprError):
    """Raised when a secret is not found."""

    error_code: str = "SECRET_NOT_FOUND"
    store_name: str | None = None
    secret_name: str | None = None

    def __str__(self) -> str:
        if self.store_name and self.secret_name:
            return f"[{self.error_code}] Secret '{self.secret_name}' not found in store '{self.store_name}'"
        return super().__str__()


@dataclass
class ActorInvocationError(DaprError):
    """Raised when an actor method invocation fails."""

    error_code: str = "ACTOR_INVOCATION_ERROR"
    actor_type: str | None = None
    actor_id: str | None = None
    method_name: str | None = None

    def __str__(self) -> str:
        parts = [f"[{self.error_code}] {self.message}"]
        if self.actor_type:
            parts.append(f"actor_type: {self.actor_type}")
        if self.actor_id:
            parts.append(f"actor_id: {self.actor_id}")
        if self.method_name:
            parts.append(f"method: {self.method_name}")
        return " ".join(parts)


@dataclass
class WorkflowError(DaprError):
    """Raised when a workflow operation fails."""

    error_code: str = "WORKFLOW_ERROR"
    workflow_name: str | None = None
    instance_id: str | None = None

    def __str__(self) -> str:
        parts = [f"[{self.error_code}] {self.message}"]
        if self.workflow_name:
            parts.append(f"workflow: {self.workflow_name}")
        if self.instance_id:
            parts.append(f"instance_id: {self.instance_id}")
        return " ".join(parts)


@dataclass
class CircuitBreakerOpenError(DaprError):
    """Raised when a circuit breaker is open."""

    error_code: str = "CIRCUIT_BREAKER_OPEN"
    target: str | None = None
    retry_after_seconds: float | None = None

    def __str__(self) -> str:
        parts = [f"[{self.error_code}] {self.message}"]
        if self.target:
            parts.append(f"target: {self.target}")
        if self.retry_after_seconds:
            parts.append(f"retry_after: {self.retry_after_seconds}s")
        return " ".join(parts)


@dataclass
class ValidationError(DaprError):
    """Raised when input validation fails."""

    error_code: str = "VALIDATION_ERROR"
    field: str | None = None
    constraint: str | None = None

    def __str__(self) -> str:
        parts = [f"[{self.error_code}] {self.message}"]
        if self.field:
            parts.append(f"field: {self.field}")
        if self.constraint:
            parts.append(f"constraint: {self.constraint}")
        return " ".join(parts)
