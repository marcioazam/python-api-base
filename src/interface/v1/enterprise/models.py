"""Enterprise examples models.

**Feature: enterprise-generics-2025**
"""

from enum import Enum

from pydantic import BaseModel


class ExampleResource(str, Enum):
    """Example resource types."""

    DOCUMENT = "document"
    REPORT = "report"
    USER = "user"


class ExampleAction(str, Enum):
    """Example actions."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"


class ExampleUser(BaseModel):
    """Example user for RBAC."""

    id: str
    email: str
    name: str
    roles: list[str]


class EmailTaskPayload(BaseModel):
    """Email task payload."""

    to: str
    subject: str
    body: str


class TaskEnqueueRequest(BaseModel):
    """Task enqueue request."""

    to: str
    subject: str
    body: str


class TaskEnqueueResponse(BaseModel):
    """Task enqueue response."""

    task_id: str
    status: str


class RateLimitCheckRequest(BaseModel):
    """Rate limit check request."""

    client_id: str


class RateLimitCheckResponse(BaseModel):
    """Rate limit check response."""

    client_id: str
    is_allowed: bool
    remaining: int
    limit: int
    reset_at: str


class RBACCheckRequest(BaseModel):
    """RBAC check request."""

    user_id: str
    user_roles: list[str]
    resource: str
    action: str


class RBACCheckResponse(BaseModel):
    """RBAC check response."""

    has_permission: bool
    checked_permission: str
    user_roles: list[str]
