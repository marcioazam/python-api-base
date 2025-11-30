"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from my_api.adapters.api.middleware.error_handler import register_exception_handlers
from my_api.adapters.api.middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from my_api.adapters.api.middleware.request_id import RequestIDMiddleware
from my_api.adapters.api.middleware.security_headers import SecurityHeadersMiddleware
from my_api.adapters.api.routes import auth, health, items
from my_api.adapters.api.versioning import APIVersion, VersionConfig, VersionedRouter
from my_api.core.config import get_settings
from my_api.core.container import Container, lifecycle
from my_api.infrastructure.database.session import init_database, close_database
from my_api.infrastructure.logging import configure_logging, get_logger
from my_api.infrastructure.observability.middleware import TracingMiddleware
from my_api.infrastructure.observability.telemetry import init_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events using the lifecycle manager.
    """
    # Startup
    settings = get_settings()
    app.state.settings = settings

    # Configure structured logging
    configure_logging(
        log_level=settings.observability.log_level,
        log_format=settings.observability.log_format,
        development=settings.debug,
    )
    logger = get_logger(__name__)

    # Initialize OpenTelemetry
    telemetry = init_telemetry(
        service_name=settings.observability.service_name,
        service_version=settings.version,
        otlp_endpoint=settings.observability.otlp_endpoint,
        enable_tracing=settings.observability.enable_tracing,
        enable_metrics=settings.observability.enable_metrics,
    )
    app.state.telemetry = telemetry
    logger.info("telemetry_initialized", service_name=settings.observability.service_name)

    # Initialize database
    logger.info("initializing_database", pool_size=settings.database.pool_size)
    db = init_database(
        database_url=settings.database.url,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        echo=settings.database.echo,
    )
    app.state.db = db

    # Check for pending migrations
    try:
        from my_api.infrastructure.database.migrations import ensure_database_ready
        await ensure_database_ready(db.engine)
    except Exception as e:
        logger.warning(f"Could not check migrations: {e}")

    # Run synchronous startup hooks
    lifecycle.run_startup()

    # Run async startup hooks
    await lifecycle.run_startup_async()

    yield

    # Shutdown - run async hooks first
    await lifecycle.run_shutdown_async()

    # Run synchronous shutdown hooks
    lifecycle.run_shutdown()

    # Gracefully shutdown telemetry
    if hasattr(app.state, "telemetry") and app.state.telemetry:
        logger.info("shutting_down_telemetry")
        await app.state.telemetry.shutdown()

    # Close database connection
    logger.info("closing_database")
    await close_database()


def _get_api_description() -> str:
    """Return API description for OpenAPI docs."""
    return """
## Modern REST API Framework

A production-ready, reusable REST API framework built with Python 3.12+ and FastAPI.

### Features

- **Generic CRUD Operations**: Type-safe, reusable endpoints for any entity
- **Clean Architecture**: Separation of concerns with domain, application, and infrastructure layers
- **Async Support**: Full async/await support throughout the stack
- **Validation**: Automatic request/response validation with Pydantic v2
- **Documentation**: Auto-generated OpenAPI documentation with examples
- **Security**: Rate limiting, CORS, security headers, and input sanitization
- **Observability**: Structured logging, distributed tracing, and health checks

### API Versioning

This API uses URL path versioning. The current version is `v1`.
All endpoints are prefixed with `/api/v1`.
    """


def _configure_middleware(app: FastAPI, settings) -> None:
    """Configure all middleware for the application."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        SecurityHeadersMiddleware,
        content_security_policy=settings.security.csp,
        permissions_policy=settings.security.permissions_policy,
    )
    app.add_middleware(
        TracingMiddleware,
        service_name=settings.observability.service_name,
        excluded_paths=["/health/live", "/health/ready", "/docs", "/redoc", "/openapi.json"],
    )
    app.add_middleware(RequestIDMiddleware)


def _configure_routes(app: FastAPI) -> None:
    """Configure routes and DI container."""
    container = Container()
    container.wire(modules=[
        "my_api.adapters.api.routes.items",
        "my_api.adapters.api.routes.health",
        "my_api.adapters.api.routes.auth",
    ])
    app.state.container = container

    v1_config = VersionConfig(version=APIVersion.V1, deprecated=False)
    v1_router = VersionedRouter(version=APIVersion.V1, config=v1_config)
    v1_router.include_router(items.router)
    v1_router.include_router(auth.router)

    app.include_router(health.router)
    app.include_router(v1_router.router)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description=_get_api_description(),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {"name": "Health", "description": "Health check endpoints"},
            {"name": "Authentication", "description": "Auth endpoints"},
            {"name": "Items", "description": "CRUD operations for Items"},
        ],
        contact={"name": "API Support", "email": "support@example.com"},
        license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        lifespan=lifespan,
    )

    _configure_middleware(app, settings)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    register_exception_handlers(app)

    _configure_routes(app)

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import os

    import uvicorn

    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("my_api.main:app", host=host, port=port, reload=True)
