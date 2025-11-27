"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from my_api.adapters.api.middleware.error_handler import register_exception_handlers
from my_api.adapters.api.middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from my_api.adapters.api.middleware.request_id import RequestIDMiddleware
from my_api.adapters.api.middleware.security_headers import SecurityHeadersMiddleware
from my_api.adapters.api.routes import health, items
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


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="""
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
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {
                "name": "Health",
                "description": "Health check endpoints for liveness and readiness probes",
            },
            {
                "name": "Items",
                "description": "CRUD operations for Item entities",
            },
        ],
        contact={
            "name": "API Support",
            "email": "support@example.com",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Add tracing middleware for OpenTelemetry
    app.add_middleware(
        TracingMiddleware,
        service_name=settings.observability.service_name,
        excluded_paths=["/health/live", "/health/ready", "/docs", "/redoc", "/openapi.json"],
    )

    # Add request ID middleware for tracing
    app.add_middleware(RequestIDMiddleware)

    # Configure rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Register exception handlers
    register_exception_handlers(app)

    # Wire DI container
    container = Container()
    container.wire(modules=[
        "my_api.adapters.api.routes.items",
        "my_api.adapters.api.routes.health",
    ])
    app.state.container = container

    # Include routers
    app.include_router(health.router)
    app.include_router(items.router, prefix="/api/v1")

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("my_api.main:app", host="0.0.0.0", port=8000, reload=True)
