"""Enterprise examples router for new PEP 695 generic modules.

**Feature: enterprise-generics-2025**

Demonstrates:
- Rate Limiter (R5)
- HTTP Client (R9)
- RBAC System (R14)
- Task Queue RabbitMQ (R3)
- OAuth Providers (R13)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from enum import Enum
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

# Rate Limiter
from infrastructure.ratelimit import (
    RateLimitConfig,
    RateLimit,
    InMemoryRateLimiter,
    RateLimitMiddleware,
    IPClientExtractor,
)

# RBAC
from infrastructure.rbac import (
    Permission,
    Role,
    RoleRegistry,
    RBAC,
    requires,
    AuditLogger,
    InMemoryAuditSink,
)

# Task Queue
from infrastructure.tasks import (
    RabbitMQConfig,
    RabbitMQTaskQueue,
    RabbitMQWorker,
    TaskHandle,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enterprise", tags=["Enterprise Examples"])


# =============================================================================
# Models
# =============================================================================


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


# =============================================================================
# Singletons (initialized on first use)
# =============================================================================

_rate_limiter: InMemoryRateLimiter[str] | None = None
_role_registry: RoleRegistry[ExampleResource, ExampleAction] | None = None
_rbac: RBAC[ExampleUser, ExampleResource, ExampleAction] | None = None
_task_queue: RabbitMQTaskQueue[EmailTaskPayload, str] | None = None
_audit_logger: AuditLogger[ExampleUser, ExampleResource, ExampleAction] | None = None


def get_rate_limiter() -> InMemoryRateLimiter[str]:
    """Get or create rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        config = RateLimitConfig(
            default_limit=RateLimit(requests=10, window=timedelta(minutes=1))
        )
        _rate_limiter = InMemoryRateLimiter[str](config)
    return _rate_limiter


def get_role_registry() -> RoleRegistry[ExampleResource, ExampleAction]:
    """Get or create role registry."""
    global _role_registry
    if _role_registry is None:
        _role_registry = RoleRegistry[ExampleResource, ExampleAction]()

        # Create viewer role
        _role_registry.create_role(
            name="viewer",
            permissions={
                Permission(ExampleResource.DOCUMENT, ExampleAction.READ),
                Permission(ExampleResource.DOCUMENT, ExampleAction.LIST),
                Permission(ExampleResource.REPORT, ExampleAction.READ),
            },
            description="Read-only access",
        )

        # Create editor role (inherits from viewer)
        _role_registry.create_role(
            name="editor",
            permissions={
                Permission(ExampleResource.DOCUMENT, ExampleAction.CREATE),
                Permission(ExampleResource.DOCUMENT, ExampleAction.UPDATE),
            },
            description="Edit access",
            parent="viewer",
        )

        # Create admin role (inherits from editor)
        _role_registry.create_role(
            name="admin",
            permissions={
                Permission(ExampleResource.DOCUMENT, ExampleAction.DELETE),
                Permission(ExampleResource.USER, ExampleAction.CREATE),
                Permission(ExampleResource.USER, ExampleAction.DELETE),
            },
            description="Full access",
            parent="editor",
        )

    return _role_registry


def get_rbac() -> RBAC[ExampleUser, ExampleResource, ExampleAction]:
    """Get or create RBAC checker."""
    global _rbac
    if _rbac is None:
        _rbac = RBAC[ExampleUser, ExampleResource, ExampleAction](get_role_registry())
    return _rbac


def get_audit_logger() -> AuditLogger[ExampleUser, ExampleResource, ExampleAction]:
    """Get or create audit logger."""
    global _audit_logger
    if _audit_logger is None:
        sink = InMemoryAuditSink()
        _audit_logger = AuditLogger[ExampleUser, ExampleResource, ExampleAction](
            sink=sink
        )
    return _audit_logger


async def get_task_queue() -> RabbitMQTaskQueue[EmailTaskPayload, str]:
    """Get or create task queue."""
    global _task_queue
    if _task_queue is None:
        config = RabbitMQConfig(
            host="localhost",
            port=5672,
            queue_name="email_tasks",
        )
        _task_queue = RabbitMQTaskQueue[EmailTaskPayload, str](
            config=config,
            task_type=EmailTaskPayload,
        )
        await _task_queue.connect()
    return _task_queue


# =============================================================================
# Rate Limiter Endpoints
# =============================================================================


@router.post(
    "/ratelimit/check",
    response_model=RateLimitCheckResponse,
    summary="Check Rate Limit",
    description="Check if a client is within rate limits.",
)
async def check_rate_limit(
    request: RateLimitCheckRequest,
) -> RateLimitCheckResponse:
    """Check rate limit for client.

    **Example: R5 - Generic Rate Limiter**

    ```python
    limiter: RateLimiter[str] = InMemoryRateLimiter(config)
    result = await limiter.check("client_123", limit)
    ```
    """
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


@router.post(
    "/ratelimit/reset/{client_id}",
    summary="Reset Rate Limit",
    description="Reset rate limit for a client.",
)
async def reset_rate_limit(client_id: str) -> dict[str, Any]:
    """Reset rate limit for client."""
    limiter = get_rate_limiter()
    success = await limiter.reset(client_id)

    return {
        "client_id": client_id,
        "reset": success,
    }


# =============================================================================
# RBAC Endpoints
# =============================================================================


@router.post(
    "/rbac/check",
    response_model=RBACCheckResponse,
    summary="Check RBAC Permission",
    description="Check if user has permission to perform action on resource.",
)
async def check_rbac_permission(
    request: RBACCheckRequest,
) -> RBACCheckResponse:
    """Check RBAC permission.

    **Example: R14 - Generic RBAC System**

    ```python
    rbac: RBAC[User, Resource, Action] = RBAC(registry)
    has_perm = rbac.has_permission(user, Permission(Resource.DOC, Action.READ))
    ```
    """
    rbac = get_rbac()

    # Create user
    user = ExampleUser(
        id=request.user_id,
        email=f"{request.user_id}@example.com",
        name="Test User",
        roles=request.user_roles,
    )

    # Parse resource and action
    try:
        resource = ExampleResource(request.resource)
        action = ExampleAction(request.action)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource '{request.resource}' or action '{request.action}'",
        )

    permission = Permission[ExampleResource, ExampleAction](
        resource=resource,
        action=action,
    )

    has_perm = rbac.has_permission(user, permission)

    # Log audit event
    audit = get_audit_logger()
    await audit.log_access(
        user_id=user.id,
        user_roles=user.roles,
        resource=resource,
        action=action,
        resource_id=None,
        granted=has_perm,
    )

    return RBACCheckResponse(
        has_permission=has_perm,
        checked_permission=str(permission),
        user_roles=request.user_roles,
    )


@router.get(
    "/rbac/roles",
    summary="List Roles",
    description="List all configured roles.",
)
async def list_roles() -> list[dict[str, Any]]:
    """List all roles."""
    registry = get_role_registry()

    return [
        {
            "name": role.name,
            "description": role.description,
            "permissions": [str(p) for p in role.permissions],
            "parent": role.parent.name if role.parent else None,
        }
        for role in registry.list()
    ]


# =============================================================================
# Task Queue Endpoints
# =============================================================================


@router.post(
    "/tasks/enqueue",
    response_model=TaskEnqueueResponse,
    summary="Enqueue Task",
    description="Enqueue an email task to RabbitMQ.",
)
async def enqueue_task(
    request: TaskEnqueueRequest,
) -> TaskEnqueueResponse:
    """Enqueue email task.

    **Example: R3 - Generic Task Queue**

    ```python
    queue: RabbitMQTaskQueue[EmailTask, str] = RabbitMQTaskQueue(config, EmailTask)
    handle = await queue.enqueue(EmailTask(to="a@b.com", subject="Hi", body="Hello"))
    result = await handle.result()
    ```
    """
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


@router.get(
    "/tasks/{task_id}/status",
    summary="Get Task Status",
    description="Get status of a queued task.",
)
async def get_task_status(task_id: str) -> dict[str, Any]:
    """Get task status."""
    queue = await get_task_queue()
    status = await queue.get_status(task_id)

    return {
        "task_id": task_id,
        "status": status.value,
    }


# =============================================================================
# HTTP Client Example (Documented)
# =============================================================================


@router.get(
    "/httpclient/example",
    summary="HTTP Client Example",
    description="Shows how to use the generic HTTP client.",
)
async def http_client_example() -> dict[str, Any]:
    """HTTP Client usage example.

    **Example: R9 - Generic HTTP Client**

    ```python
    from infrastructure.httpclient import HttpClient, HttpClientConfig

    class CreateUserRequest(BaseModel):
        name: str
        email: str

    class UserResponse(BaseModel):
        id: str
        name: str
        email: str

    config = HttpClientConfig(
        base_url="https://api.example.com",
        timeout=timedelta(seconds=30),
    )

    async with HttpClient[CreateUserRequest, UserResponse](
        config=config,
        response_type=UserResponse,
    ) as client:
        user = await client.post("/users", CreateUserRequest(name="John", email="j@e.com"))
        print(user.id)  # Type-safe: UserResponse
    ```
    """
    return {
        "description": "Generic HTTP Client with PEP 695 type parameters",
        "features": [
            "HttpClient[TRequest, TResponse] - Typed request/response",
            "Automatic JSON serialization via Pydantic",
            "Circuit breaker integration",
            "Retry with exponential backoff",
            "Typed errors: TimeoutError[TRequest], ValidationError[TResponse]",
        ],
        "example_code": """
async with HttpClient[CreateUserRequest, UserResponse](config, UserResponse) as client:
    user = await client.post("/users", CreateUserRequest(name="John", email="j@e.com"))
""",
    }


# =============================================================================
# OAuth Example (Documented)
# =============================================================================


@router.get(
    "/oauth/example",
    summary="OAuth Provider Example",
    description="Shows how to use the generic OAuth providers.",
)
async def oauth_example() -> dict[str, Any]:
    """OAuth Provider usage example.

    **Example: R13 - Generic Authentication System**

    ```python
    from infrastructure.auth.oauth import KeycloakProvider, KeycloakConfig

    class User(BaseModel):
        id: str
        email: str
        name: str

    class Claims(BaseModel):
        sub: str
        email: str
        realm_access: dict[str, list[str]]

    config = KeycloakConfig(
        server_url="https://keycloak.example.com",
        realm="myrealm",
        client_id="myapp",
        client_secret="secret",
    )

    provider = KeycloakProvider[User, Claims](
        config=config,
        user_type=User,
        claims_type=Claims,
    )

    result = await provider.authenticate(PasswordCredentials(
        username="user@example.com",
        password="password",
    ))

    if result.success:
        user = result.user  # Type: User
        claims = result.claims  # Type: Claims
        tokens = result.tokens  # Type: TokenPair[Claims]
    ```
    """
    return {
        "description": "Generic OAuth Providers with PEP 695 type parameters",
        "providers": [
            "KeycloakProvider[TUser, TClaims] - Keycloak integration",
            "Auth0Provider[TUser, TClaims] - Auth0 integration",
        ],
        "features": [
            "OAuthProvider[TUser, TClaims] - Generic provider protocol",
            "AuthResult[TUser, TClaims] - Typed authentication result",
            "TokenPair[TClaims] - Typed access/refresh tokens",
            "Password and authorization code flows",
            "Token validation and refresh",
            "Role/permission extraction from claims",
        ],
        "docker": {
            "keycloak": "http://localhost:8080",
            "admin_user": "admin",
            "admin_password": "admin",
        },
    }


# =============================================================================
# Kafka Transactional Example (Documented)
# =============================================================================


@router.get(
    "/kafka/transactional/example",
    summary="Kafka Transactional Producer Example",
    description="Shows how to use the transactional Kafka producer with exactly-once semantics.",
)
async def kafka_transactional_example() -> dict[str, Any]:
    """Kafka Transactional Producer usage example.

    **Requirement: R3.1 - Transactional Producer with Exactly-Once Semantics**

    ```python
    from infrastructure.kafka import (
        KafkaConfig,
        TransactionalKafkaProducer,
        TransactionState,
    )

    class OrderEvent(BaseModel):
        order_id: str
        status: str
        amount: float

    config = KafkaConfig(
        bootstrap_servers=["localhost:9092"],
        client_id="order-service",
    )

    # Transactional producer with exactly-once semantics
    async with TransactionalKafkaProducer[OrderEvent](
        config=config,
        topic="orders",
        transactional_id="order-processor-1",  # Unique per instance
    ) as producer:
        # All messages in transaction are atomic
        async with producer.transaction() as tx:
            await tx.send(OrderEvent(order_id="123", status="created", amount=99.99))
            await tx.send(OrderEvent(order_id="123", status="paid", amount=99.99))
            # If exception occurs here, both messages are rolled back

        # Transaction committed - both messages delivered exactly-once
        print(f"Transaction state: {producer.transaction_state}")
    ```
    """
    return {
        "description": "Kafka Transactional Producer with Exactly-Once Semantics",
        "features": [
            "TransactionalKafkaProducer[T] - Type-safe transactional producer",
            "transaction() context manager - Atomic message delivery",
            "TransactionContext[T] - Send messages within transaction",
            "Exactly-once semantics via idempotence + transactions",
            "Automatic rollback on exception",
            "TransactionState tracking (IDLE, STARTED, COMMITTED, ABORTED)",
        ],
        "configuration": {
            "transactional_id": "Unique ID per producer instance",
            "enable_idempotence": "Automatically enabled (True)",
            "acks": "Set to 'all' for durability",
        },
        "use_cases": [
            "Financial transactions (debits + credits)",
            "Order processing (create + update)",
            "Multi-topic atomic writes",
            "Saga pattern implementation",
        ],
        "docker": {
            "kafka": "localhost:9092",
            "start": "docker compose -f docker/docker-compose.observability.yml up kafka -d",
        },
    }


# =============================================================================
# Serverless Deployment Example (Documented)
# =============================================================================


@router.get(
    "/serverless/example",
    summary="Serverless Deployment Example",
    description="Shows how to deploy the API to AWS Lambda and Vercel.",
)
async def serverless_example() -> dict[str, Any]:
    """Serverless deployment examples.

    **AWS Lambda:**
    ```bash
    # Build and deploy with SAM
    sam build --template deployments/serverless/aws-lambda/template.yaml
    sam deploy --guided
    ```

    **Vercel:**
    ```bash
    cd deployments/serverless/vercel
    vercel --prod
    ```
    """
    return {
        "description": "Serverless Deployment Adapters",
        "platforms": {
            "aws_lambda": {
                "handler": "deployments.serverless.aws_lambda.handler.handler",
                "adapter": "Mangum (ASGI to Lambda)",
                "deploy": "sam build && sam deploy --guided",
                "features": [
                    "API Gateway HTTP API v2 support",
                    "VPC configuration for database access",
                    "Secrets Manager integration",
                    "X-Ray tracing",
                ],
            },
            "vercel": {
                "handler": "api/index.py",
                "adapter": "Native Python runtime",
                "deploy": "vercel --prod",
                "features": [
                    "Edge network distribution",
                    "Automatic HTTPS",
                    "Environment variables via dashboard",
                    "Preview deployments",
                ],
            },
        },
        "considerations": [
            "Use connection poolers (PgBouncer, RDS Proxy) for databases",
            "Minimize cold starts with lazy imports",
            "Keep dependencies minimal",
            "Use serverless-friendly databases (Neon, Supabase)",
        ],
        "files": {
            "lambda": "deployments/serverless/aws-lambda/",
            "vercel": "deployments/serverless/vercel/",
        },
    }
