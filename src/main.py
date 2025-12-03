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
from infrastructure.di.cqrs_bootstrap import bootstrap_cqrs
from infrastructure.di.examples_bootstrap import bootstrap_examples
from infrastructure.db.repositories.examples import (
    ItemExampleRepository,
    PedidoExampleRepository,
)
from infrastructure.db.session import get_database_session
from infrastructure.di.app_container import create_container
from infrastructure.db.session import init_database, close_database
from infrastructure.observability import LoggingMiddleware
from interface.middleware.production import (
    AuditConfig,
    MultitenancyConfig,
    ResilienceConfig,
    setup_production_middleware,
)
from interface.middleware.security import SecurityHeadersMiddleware
from interface.middleware.request import (
    RequestIDMiddleware,
    RequestSizeLimitMiddleware,
)
from interface.middleware.logging import RequestLoggerMiddleware
from interface.v1.health_router import router as health_router, mark_startup_complete
from interface.openapi import setup_openapi
from core.errors import setup_exception_handlers
from infrastructure.redis import RedisClient, RedisConfig
from infrastructure.minio import MinIOClient, MinIOConfig
from infrastructure.kafka import KafkaProducer, KafkaConfig
from infrastructure.prometheus import setup_prometheus
from infrastructure.ratelimit import (
    RateLimitMiddleware,
    InMemoryRateLimiter,
    RateLimitConfig,
    RateLimit,
    IPClientExtractor,
)

# Core API Routes (permanent - do not remove)
from interface.v1.auth import auth_router
from interface.v1.users_router import router as users_router

# Example System - Remove for production
# See docs/example-system-deactivation.md
from interface.v1.examples import examples_router
from interface.v1.infrastructure_router import router as infrastructure_router
from interface.v1.enterprise_examples_router import router as enterprise_router

# API v2 Routes
# **Feature: interface-modules-workflow-analysis**
# **Validates: Requirements 1.1, 1.2, 1.3**
from interface.v2 import examples_v2_router

# GraphQL Support (optional - requires strawberry)
# **Feature: interface-modules-workflow-analysis**
# **Validates: Requirements 3.1, 3.2, 3.3**
try:
    from interface.graphql import graphql_router, HAS_STRAWBERRY
except ImportError:
    graphql_router = None
    HAS_STRAWBERRY = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events using the lifecycle manager.
    """
    settings = get_settings()
    app.state.settings = settings
    logger = get_logger("main")

    lifecycle.run_startup()
    await lifecycle.run_startup_async()

    # Initialize database
    logger.info("Initializing database...")
    init_database(
        database_url=settings.database.url,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        echo=settings.database.echo,
    )
    logger.info("Database initialized")

    # Bootstrap CQRS handlers
    logger.info("Bootstrapping CQRS handlers...")
    container = create_container(settings)
    command_bus = container.command_bus()
    query_bus = container.query_bus()
    await bootstrap_cqrs(command_bus=command_bus, query_bus=query_bus)
    logger.info("CQRS handlers bootstrapped")

    # Bootstrap Example handlers
    # **Feature: infrastructure-examples-integration-fix**
    # **Validates: Requirements 3.1, 3.2, 3.3**
    logger.info("Bootstrapping example handlers...")
    db = get_database_session()
    async with db.session() as session:
        item_repo = ItemExampleRepository(session)
        pedido_repo = PedidoExampleRepository(session)
        await bootstrap_examples(
            command_bus=command_bus,
            query_bus=query_bus,
            item_repository=item_repo,
            pedido_repository=pedido_repo,
        )
    logger.info("Example handlers bootstrapped")

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

    # Initialize Kafka if enabled
    # **Feature: kafka-workflow-integration**
    # **Validates: Requirements 1.1, 1.2, 1.3, 1.5**
    if obs.kafka_enabled:
        kafka_config = KafkaConfig(
            bootstrap_servers=obs.kafka_bootstrap_servers,
            client_id=obs.kafka_client_id,
            group_id=obs.kafka_group_id,
            security_protocol=obs.kafka_security_protocol,
            sasl_mechanism=obs.kafka_sasl_mechanism,
            sasl_username=obs.kafka_sasl_username,
            sasl_password=obs.kafka_sasl_password.get_secret_value()
            if obs.kafka_sasl_password
            else None,
        )
        app.state.kafka_producer = KafkaProducer(kafka_config, topic="default-events")
        try:
            await app.state.kafka_producer.start()
            logger.info("Kafka producer started")
        except Exception as e:
            logger.error(f"Kafka connection failed: {e}")
            app.state.kafka_producer = None
    else:
        app.state.kafka_producer = None
        logger.info("Kafka disabled, skipping initialization")

    # Initialize ScyllaDB if enabled
    # **Feature: infrastructure-modules-workflow-analysis**
    # **Validates: Requirements 1.1**
    if obs.scylladb_enabled:
        from infrastructure.scylladb import ScyllaDBClient, ScyllaDBConfig
        scylladb_config = ScyllaDBConfig(
            hosts=obs.scylladb_hosts,
            port=obs.scylladb_port,
            keyspace=obs.scylladb_keyspace,
            username=obs.scylladb_username,
            password=obs.scylladb_password.get_secret_value()
            if obs.scylladb_password
            else None,
            protocol_version=obs.scylladb_protocol_version,
            connect_timeout=obs.scylladb_connect_timeout,
            request_timeout=obs.scylladb_request_timeout,
        )
        app.state.scylladb = ScyllaDBClient(scylladb_config)
        try:
            await app.state.scylladb.connect()
            logger.info("ScyllaDB client connected")
        except Exception as e:
            logger.error(f"ScyllaDB connection failed: {e}")
            app.state.scylladb = None
    else:
        app.state.scylladb = None
        logger.info("ScyllaDB disabled, skipping initialization")

    # Initialize RabbitMQ if enabled
    # **Feature: infrastructure-modules-workflow-analysis**
    # **Validates: Requirements 3.4**
    if obs.rabbitmq_enabled:
        from infrastructure.tasks import RabbitMQConfig, RabbitMQTaskQueue
        rabbitmq_config = RabbitMQConfig(
            host=obs.rabbitmq_host,
            port=obs.rabbitmq_port,
            username=obs.rabbitmq_username,
            password=obs.rabbitmq_password.get_secret_value()
            if obs.rabbitmq_password
            else None,
            virtual_host=obs.rabbitmq_virtual_host,
        )
        app.state.rabbitmq = rabbitmq_config  # Store config, lazy connect
        logger.info("RabbitMQ config stored (lazy connection)")
    else:
        app.state.rabbitmq = None
        logger.info("RabbitMQ disabled, skipping initialization")

    # Mark startup complete for Kubernetes probe
    mark_startup_complete()

    yield

    # Cleanup
    if app.state.redis:
        await app.state.redis.close()

    # Cleanup Kafka
    # **Feature: kafka-workflow-integration**
    # **Validates: Requirements 1.4**
    if app.state.kafka_producer:
        await app.state.kafka_producer.stop()
        logger.info("Kafka producer stopped")

    # Cleanup ScyllaDB
    # **Feature: infrastructure-modules-workflow-analysis**
    # **Validates: Requirements 1.1**
    if hasattr(app.state, 'scylladb') and app.state.scylladb:
        await app.state.scylladb.close()
        logger.info("ScyllaDB client closed")

    # Close database
    logger.info("Closing database...")
    await close_database()
    logger.info("Database closed")

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

    **Feature: interface-middleware-routes-analysis**
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4**

    Middleware stack order (outermost to innermost):
    1. RequestIDMiddleware - Generate/propagate X-Request-ID
    2. LoggingMiddleware - Correlation ID and structured logging
    3. RequestLoggerMiddleware - Request/response logging with PII masking
    4. CORSMiddleware - Cross-origin resource sharing
    5. SecurityHeadersMiddleware - Security headers (CSP, HSTS, etc.)
    6. RequestSizeLimitMiddleware - Limit request body size
    7. ResilienceMiddleware - Circuit breaker pattern
    8. MultitenancyMiddleware - Tenant context resolution
    9. AuditMiddleware - Request audit trail
    10. RateLimitMiddleware - Rate limiting
    """
    settings = get_settings()
    logger = get_logger("main")

    # 1. RequestIDMiddleware - First middleware to generate/propagate X-Request-ID
    # **Feature: interface-middleware-routes-analysis**
    # **Validates: Requirements 1.1**
    app.add_middleware(RequestIDMiddleware)
    logger.info("middleware_configured", middleware="RequestIDMiddleware")

    # 2. Logging middleware (correlation ID, request logging)
    app.add_middleware(
        LoggingMiddleware,
        service_name=settings.observability.service_name,
        excluded_paths=["/health/live", "/health/ready", "/metrics", "/docs", "/redoc"],
    )
    logger.info("middleware_configured", middleware="LoggingMiddleware")

    # 3. RequestLoggerMiddleware - Detailed request/response logging with PII masking
    # **Feature: interface-middleware-routes-analysis**
    # **Validates: Requirements 1.2**
    app.add_middleware(
        RequestLoggerMiddleware,
        log_request_body=False,
        log_response_body=False,
        excluded_paths=["/health/live", "/health/ready", "/metrics", "/docs", "/redoc", "/openapi.json"],
    )
    logger.info("middleware_configured", middleware="RequestLoggerMiddleware")

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

    # 5. Security headers middleware
    # Protects against XSS, clickjacking, MIME sniffing attacks
    #
    # CSP Note: 'unsafe-inline' and 'unsafe-eval' are required for:
    # - Swagger UI (/docs): Inline styles and dynamic script evaluation
    # - ReDoc (/redoc): Inline styles for rendering
    # Trade-off: Accepted for development/documentation tools only.
    # Production API endpoints remain protected by strict CSP.
    # Alternative: Use nonce-based CSP for tighter security (requires code changes).
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
    logger.info("middleware_configured", middleware="SecurityHeadersMiddleware")

    # 6. RequestSizeLimitMiddleware - Limit request body size (10MB default)
    # **Feature: interface-middleware-routes-analysis**
    # **Validates: Requirements 1.4**
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_size=10 * 1024 * 1024,  # 10MB default
        route_limits={
            r"^/api/v1/upload.*": 50 * 1024 * 1024,  # 50MB for uploads
            r"^/api/v1/import.*": 20 * 1024 * 1024,  # 20MB for imports
        },
    )
    logger.info("middleware_configured", middleware="RequestSizeLimitMiddleware", max_size="10MB")

    # 7-9. Production middleware stack
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


def _configure_rate_limiting(app: FastAPI) -> None:
    """Configure rate limiting middleware.

    **Feature: infrastructure-modules-integration-analysis**
    **Validates: Requirements 1.3**

    Sets up:
    - InMemoryRateLimiter for request rate limiting
    - Per-endpoint limits for different operations
    """
    from datetime import timedelta

    logger = get_logger("main")

    # Configure rate limits
    config = RateLimitConfig(
        default_limit=RateLimit(requests=100, window=timedelta(minutes=1))
    )
    limiter = InMemoryRateLimiter[str](config)

    # Configure per-endpoint limits
    limiter.configure({
        "GET:/api/v1/examples/*": RateLimit(requests=100, window=timedelta(minutes=1)),
        "POST:/api/v1/examples/*": RateLimit(requests=20, window=timedelta(minutes=1)),
        "PUT:/api/v1/examples/*": RateLimit(requests=20, window=timedelta(minutes=1)),
        "DELETE:/api/v1/examples/*": RateLimit(requests=10, window=timedelta(minutes=1)),
    })

    app.add_middleware(
        RateLimitMiddleware[str],
        limiter=limiter,
        extractor=IPClientExtractor(),
        exclude_paths={"/health", "/health/live", "/health/ready", "/metrics", "/docs", "/redoc", "/openapi.json"},
    )

    logger.info("rate_limiting_configured", default_limit="100/min")


def _configure_prometheus(app: FastAPI) -> None:
    """Configure Prometheus metrics if enabled.

    **Feature: infrastructure-modules-integration-analysis**
    **Validates: Requirements 1.1, 1.2**

    Sets up:
    - PrometheusMiddleware for request metrics collection
    - /metrics endpoint for Prometheus scraping
    """
    settings = get_settings()
    obs = settings.observability
    logger = get_logger("main")

    if obs.prometheus_enabled:
        setup_prometheus(
            app,
            endpoint=obs.prometheus_endpoint,
            include_in_schema=obs.prometheus_include_in_schema,
            skip_paths=["/health/live", "/health/ready", "/docs", "/redoc"],
        )
        logger.info(
            "prometheus_configured",
            endpoint=obs.prometheus_endpoint,
            namespace=obs.prometheus_namespace,
        )
    else:
        logger.info("prometheus_disabled", reason="prometheus_enabled=false")


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

    # Configure Prometheus metrics
    # **Feature: infrastructure-modules-integration-analysis**
    # **Validates: Requirements 1.1, 1.2**
    _configure_prometheus(app)

    # Configure rate limiting
    # **Feature: infrastructure-modules-integration-analysis**
    # **Validates: Requirements 1.3**
    _configure_rate_limiting(app)

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

    # API v2 Routes with versioning support
    # **Feature: interface-modules-workflow-analysis**
    # **Validates: Requirements 1.1, 1.2, 1.3**
    app.include_router(examples_v2_router, prefix="/api")

    # GraphQL endpoint (optional)
    # **Feature: interface-modules-workflow-analysis**
    # **Validates: Requirements 3.1, 3.2, 3.3**
    if HAS_STRAWBERRY and graphql_router is not None:
        app.include_router(graphql_router, prefix="/api", tags=["GraphQL"])
        logger.info("graphql_enabled", endpoint="/api/graphql")
    else:
        logger.info("graphql_disabled", reason="strawberry not installed")

    return app


app = create_app()


if __name__ == "__main__":
    import os

    import uvicorn

    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
