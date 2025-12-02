"""Documentation endpoints for enterprise examples.

**Feature: enterprise-generics-2025**
"""

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["Documentation"])


@router.get("/httpclient/example", summary="HTTP Client Example")
async def http_client_example() -> dict[str, Any]:
    """HTTP Client usage example."""
    return {
        "description": "Generic HTTP Client with PEP 695 type parameters",
        "features": [
            "HttpClient[TRequest, TResponse] - Typed request/response",
            "Automatic JSON serialization via Pydantic",
            "Circuit breaker integration",
            "Retry with exponential backoff",
        ],
    }


@router.get("/oauth/example", summary="OAuth Provider Example")
async def oauth_example() -> dict[str, Any]:
    """OAuth Provider usage example."""
    return {
        "description": "Generic OAuth Providers with PEP 695 type parameters",
        "providers": [
            "KeycloakProvider[TUser, TClaims]",
            "Auth0Provider[TUser, TClaims]",
        ],
        "features": [
            "OAuthProvider[TUser, TClaims] - Generic provider protocol",
            "AuthResult[TUser, TClaims] - Typed authentication result",
            "TokenPair[TClaims] - Typed access/refresh tokens",
        ],
    }


@router.get("/kafka/transactional/example", summary="Kafka Transactional Example")
async def kafka_transactional_example() -> dict[str, Any]:
    """Kafka Transactional Producer usage example."""
    return {
        "description": "Kafka Transactional Producer with Exactly-Once Semantics",
        "features": [
            "TransactionalKafkaProducer[T] - Type-safe transactional producer",
            "transaction() context manager - Atomic message delivery",
            "Exactly-once semantics via idempotence + transactions",
        ],
    }


@router.get("/serverless/example", summary="Serverless Deployment Example")
async def serverless_example() -> dict[str, Any]:
    """Serverless deployment examples."""
    return {
        "description": "Serverless Deployment Adapters",
        "platforms": {
            "aws_lambda": {"adapter": "Mangum (ASGI to Lambda)"},
            "vercel": {"adapter": "Native Python runtime"},
        },
    }
