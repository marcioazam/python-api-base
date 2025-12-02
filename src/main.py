"""FastAPI application entry point.

This module provides the main application factory and lifespan management.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 13, 16, 18, 19, 22**
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.shared.logging import configure_logging, get_logger
from infrastructure.audit import InMemoryAuditStore
from infrastructure.di import lifecycle
from infrastructure.observability import LoggingMiddleware
from interface.middleware.production import (
    AuditConfig,
    MultitenancyConfig,
    ResilienceConfig,
    setup_production_middleware,
)
from interface.middleware.security_headers import SecurityHeadersMiddleware
from interface.v1.health_router import router as health_router, mark_startup_complete
from interface.openapi import setup_openapi
from core.errors import setup_exception_handlers
from infrastructure.redis import RedisClient, RedisConfig
from infrastructure.minio import MinIOClient, MinIOConfig

# Core API Routes (permanent - do not remove)
from interface.v1.auth import auth_router, users_router

# Example System - Remove for production
# See docs/example-system-deactivation.md
from interface.v1.examples import examples_router
from interface.v1.infrastructure_router import router as infrastructure_router
from interface.v1.enterprise_examples_router import router as enterprise_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events using the lifecycle manager.
    """
    settings = get_settings()
    app.state.settings = settings

    lifecycle.run_startup()
    await lifecycle.run_startup_async()

    # Initialize Redis if enabled
    obs = settings.observability
    if obs.redis_enabled:
        redis_config = RedisConfig(
            url=obs.redis_url,
            pool_max_size=obs.redis_pool_size,
            key_prefix=obs.redis_key_prefix,
        )
        app.state.redis = RedisClient(redis_config)
        await app.state.redis.connect()
    else:
        app.state.redis = None

    # Initialize MinIO if enabled
    if obs.minio_enabled:
        minio_config = MinIOConfig(
            endpoint=obs.minio_endpoint,
            access_key=obs.minio_access_key,
            secret_key=obs.minio_secret_key.get_secret_value(),
            bucket=obs.minio_bucket,
            secure=obs.minio_secure,
        )
        app.state.minio = MinIOClient(minio_config)
        await app.state.minio.connect()
    else:
        app.state.minio = None

    # Mark startup complete for Kubernetes probe
    mark_startup_complete()

    yield

    # Cleanup
    if app.state.redis:
        await app.state.redis.close()

    await lifecycle.run_shutdown_async()
    lifecycle.run_shutdown()


def _configure_logging() -> None:
    """Configure structured logging with ECS compatibility.

    Sets up structlog with:
    - JSON output format (or console for debug)
    - ECS-compatible field names
    - PII redaction
    - Correlation ID support
    """
    settings = get_settings()
    obs = settings.observability

    configure_logging(
        log_level=obs.log_level,
        json_output=obs.log_format == "json",
        add_ecs_fields=obs.log_ecs_format,
        service_name=obs.service_name,
        service_version=obs.service_version,
        environment=obs.environment,
    )

    logger = get_logger("main")
    logger.info(
        "logging_configured",
        log_level=obs.log_level,
        log_format=obs.log_format,
        ecs_enabled=obs.log_ecs_format,
        elasticsearch_enabled=obs.elasticsearch_enabled,
    )


def _configure_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application.

    Includes:
    - Logging middleware (correlation ID, request logging)
    - CORS middleware
    - Production middleware stack (resilience, multitenancy, audit)
    """
    settings = get_settings()

    # Logging middleware (first - to capture all requests)
    app.add_middleware(
        LoggingMiddleware,
        service_name=settings.observability.service_name,
        excluded_paths=["/health/live", "/health/ready", "/metrics", "/docs", "/redoc"],
    )

    # CORS middleware
    # Security validation: wildcard origins + credentials = security vulnerability
    if "*" in settings.security.cors_origins:
        error_msg = (
            "CRITICAL SECURITY ERROR: CORS allow_credentials=True requires specific "
            "origins, not wildcard ['*']. This combination allows any origin to send "
            "credentials, enabling CSRF attacks. Set SECURITY__CORS_ORIGINS to specific "
            "domains (e.g., ['https://app.example.com', 'https://admin.example.com'])"
        )
        logger.error("cors_security_violation", error=error_msg)
        raise ValueError(error_msg)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security headers middleware
    # Protects against XSS, clickjacking, MIME sniffing attacks
    app.add_middleware(
        SecurityHeadersMiddleware,
        content_security_policy=(
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https://cdn.jsdelivr.net; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        ),
        x_frame_options="DENY",
        x_content_type_options="nosniff",
        x_xss_protection="1; mode=block",
        strict_transport_security="max-age=31536000; includeSubDomains; preload",
        referrer_policy="strict-origin-when-cross-origin",
        permissions_policy=(
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        ),
    )

    # Production middleware stack (optional - enable as needed)
    # Provides: Resilience, Multitenancy, Feature Flags, Audit Trail
    setup_production_middleware(
        app,
        resilience_config=ResilienceConfig(
            failure_threshold=5,
            timeout_seconds=30.0,
            enabled=True,
        ),
        multitenancy_config=MultitenancyConfig(
            required=False,  # Set to True for strict multitenancy
            header_name="X-Tenant-ID",
        ),
        audit_store=InMemoryAuditStore(),
        audit_config=AuditConfig(
            enabled=True,
            exclude_paths={"/health", "/metrics", "/docs", "/redoc", "/openapi.json"},
        ),
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Configure logging first (before any other initialization)
    _configure_logging()

    settings = get_settings()
    logger = get_logger("main")

    logger.info(
        "creating_application", app_name=settings.app_name, version=settings.version
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Modern REST API Framework with PEP 695 Generics",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Setup exception handlers (RFC 7807)
    setup_exception_handlers(app)

    # Setup OpenAPI customization
    setup_openapi(app)

    _configure_middleware(app)
    app.include_router(health_router)

    # Core API Routes (permanent - do not remove)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")

    # Example System Routes - Remove for production
    # See docs/example-system-deactivation.md
    app.include_router(examples_router, prefix="/api/v1")

    # Infrastructure Examples (Redis, MinIO)
    app.include_router(infrastructure_router, prefix="/api/v1")

    # Enterprise Examples (Rate Limiter, RBAC, Task Queue, OAuth)
    app.include_router(enterprise_router, prefix="/api/v1")

    return app


app = create_app()


if __name__ == "__main__":
    import os

    import uvicorn

    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
