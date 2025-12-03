"""CQRS handler registration bootstrap.

This module registers all command and query handlers to their respective buses.
Uses a lazy initialization pattern where repository instances are created
per-handler-call from the global database session.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 5.3, 5.5**
"""

import logging
import os

from application.common.cqrs import CommandBus, QueryBus
from application.common.middleware.resilience import ResilienceMiddleware
from application.common.middleware.retry import RetryConfig
from application.common.middleware.circuit_breaker import CircuitBreakerConfig
from application.common.middleware.observability import (
    LoggingMiddleware,
    LoggingConfig,
    MetricsMiddleware,
    MetricsConfig,
    InMemoryMetricsCollector,
)
from application.common.middleware.query_cache import (
    QueryCacheMiddleware,
    QueryCacheConfig,
    InMemoryQueryCache,
)
from application.users.commands import (
    CreateUserCommand,
    CreateUserHandler,
    UpdateUserCommand,
    UpdateUserHandler,
    DeleteUserCommand,
    DeleteUserHandler,
)
from application.users.queries import (
    GetUserByIdQuery,
    GetUserByIdHandler,
    GetUserByEmailQuery,
    GetUserByEmailHandler,
    ListUsersQuery,
    ListUsersHandler,
)
from domain.users.services import UserDomainService
from infrastructure.db.session import get_database_session
from infrastructure.db.repositories.user_repository import SQLAlchemyUserRepository
from infrastructure.db.repositories.user_read_repository import (
    SQLAlchemyUserReadRepository,
)

logger = logging.getLogger(__name__)


async def register_user_handlers(
    command_bus: CommandBus,
    query_bus: QueryBus,
) -> None:
    """Register all user-related command and query handlers.

    Handlers are registered with factory functions that create
    repository instances per-call using the global database session.

    Args:
        command_bus: CommandBus instance to register command handlers to.
        query_bus: QueryBus instance to register query handlers to.
    """
    # Create user domain service instance (stateless)
    user_service = UserDomainService()

    # Register command handlers with factory pattern
    async def create_user_handler(cmd: CreateUserCommand):
        """Factory for CreateUserHandler with fresh repository."""
        db = get_database_session()
        async with db.session() as session:
            repo = SQLAlchemyUserRepository(session)
            handler = CreateUserHandler(
                user_repository=repo,
                user_service=user_service,
            )
            return await handler.handle(cmd)

    command_bus.register(CreateUserCommand, create_user_handler)
    logger.info("Registered CreateUserHandler")

    async def update_user_handler(cmd: UpdateUserCommand):
        """Factory for UpdateUserHandler with fresh repository."""
        db = get_database_session()
        async with db.session() as session:
            repo = SQLAlchemyUserRepository(session)
            handler = UpdateUserHandler(user_repository=repo)
            return await handler.handle(cmd)

    command_bus.register(UpdateUserCommand, update_user_handler)
    logger.info("Registered UpdateUserHandler")

    async def delete_user_handler(cmd: DeleteUserCommand):
        """Factory for DeleteUserHandler with fresh repository."""
        db = get_database_session()
        async with db.session() as session:
            repo = SQLAlchemyUserRepository(session)
            handler = DeleteUserHandler(user_repository=repo)
            return await handler.handle(cmd)

    command_bus.register(DeleteUserCommand, delete_user_handler)
    logger.info("Registered DeleteUserHandler")

    # Register query handlers with factory pattern
    async def get_user_by_id_handler(query: GetUserByIdQuery):
        """Factory for GetUserByIdHandler with fresh repository."""
        db = get_database_session()
        async with db.session() as session:
            repo = SQLAlchemyUserRepository(session)
            handler = GetUserByIdHandler(repository=repo)
            return await handler.handle(query)

    query_bus.register(GetUserByIdQuery, get_user_by_id_handler)
    logger.info("Registered GetUserByIdHandler")

    async def get_user_by_email_handler(query: GetUserByEmailQuery):
        """Factory for GetUserByEmailHandler with fresh repository."""
        db = get_database_session()
        async with db.session() as session:
            repo = SQLAlchemyUserRepository(session)
            handler = GetUserByEmailHandler(repository=repo)
            return await handler.handle(query)

    query_bus.register(GetUserByEmailQuery, get_user_by_email_handler)
    logger.info("Registered GetUserByEmailHandler")

    async def list_users_handler(query: ListUsersQuery):
        """Factory for ListUsersHandler with fresh repository."""
        db = get_database_session()
        async with db.session() as session:
            repo = SQLAlchemyUserReadRepository(session)
            handler = ListUsersHandler(read_repository=repo)
            return await handler.handle(query)

    query_bus.register(ListUsersQuery, list_users_handler)
    logger.info("Registered ListUsersHandler")

    logger.info("All user handlers registered successfully")


def configure_cqrs_middleware(
    command_bus: CommandBus,
    query_bus: QueryBus,
    enable_resilience: bool = False,
    enable_observability: bool = True,
    enable_query_cache: bool = True,
) -> None:
    """Configure middleware for CQRS buses.

    Middleware is applied in order:
    1. Observability (logging + metrics) - outer layer
    2. Query cache (for QueryBus only) - middle layer
    3. Resilience (circuit breaker + retry) - inner layer

    This ensures that all operations are logged and measured,
    even when circuit breaker is open or retries are happening.

    Args:
        command_bus: CommandBus instance to configure.
        query_bus: QueryBus instance to configure.
        enable_resilience: Enable retry and circuit breaker (default: False).
            See ADR-003 for rationale on why this is disabled by default.
        enable_observability: Enable logging and metrics (default: True).
        enable_query_cache: Enable query result caching (default: True).

    Note:
        Resilience is disabled by default as per ADR-003. The HTTP layer
        already provides resilience. CQRS resilience is available for
        domain-specific scenarios when needed.
    """
    logger.info("Configuring CQRS middleware...")

    # Layer 2: Resilience (optional, inner layer)
    if enable_resilience:
        retry_config = RetryConfig(
            max_retries=int(os.getenv("CQRS_RETRY_MAX_RETRIES", "3")),
            base_delay=float(os.getenv("CQRS_RETRY_BASE_DELAY", "1.0")),
            max_delay=float(os.getenv("CQRS_RETRY_MAX_DELAY", "30.0")),
        )

        circuit_config = CircuitBreakerConfig(
            failure_threshold=int(os.getenv("CQRS_CIRCUIT_FAILURE_THRESHOLD", "5")),
            recovery_timeout=float(os.getenv("CQRS_CIRCUIT_RECOVERY_TIMEOUT", "60.0")),
        )

        resilience_middleware = ResilienceMiddleware(
            retry_config=retry_config,
            circuit_config=circuit_config,
        )

        command_bus.add_middleware(resilience_middleware)
        logger.info(
            "CQRS resilience middleware enabled",
            extra={
                "max_retries": retry_config.max_retries,
                "circuit_threshold": circuit_config.failure_threshold,
            },
        )
    else:
        logger.info(
            "CQRS resilience middleware disabled (HTTP layer provides resilience)"
        )

    # Layer 1: Observability (outer layer)
    if enable_observability:
        # Logging middleware
        logging_config = LoggingConfig(
            log_request=True,
            log_response=True,
            log_duration=True,
            include_command_data=os.getenv("CQRS_LOG_COMMAND_DATA", "false").lower()
            == "true",
        )

        logging_middleware = LoggingMiddleware(logging_config)
        command_bus.add_middleware(logging_middleware)
        query_bus.add_middleware(logging_middleware)

        # Metrics middleware
        metrics_collector = InMemoryMetricsCollector()
        metrics_config = MetricsConfig(
            enabled=True,
            track_duration=True,
            track_success_rate=True,
            detect_slow_commands=True,
            slow_threshold_ms=float(
                os.getenv("CQRS_SLOW_THRESHOLD_MS", "1000.0")
            ),
        )

        metrics_middleware = MetricsMiddleware(metrics_collector, metrics_config)
        command_bus.add_middleware(metrics_middleware)
        query_bus.add_middleware(metrics_middleware)

        logger.info("CQRS observability middleware enabled")

    # Query Cache (for QueryBus only)
    if enable_query_cache:
        query_cache = InMemoryQueryCache()
        cache_config = QueryCacheConfig(
            ttl_seconds=int(os.getenv("QUERY_CACHE_TTL_SECONDS", "300")),  # 5 min
            key_prefix="query_cache",
            enabled=True,
            cache_all_queries=os.getenv("CACHE_ALL_QUERIES", "false").lower()
            == "true",
            log_hits=True,
            log_misses=False,
        )

        cache_middleware = QueryCacheMiddleware(query_cache, cache_config)
        query_bus.add_middleware(cache_middleware)

        logger.info(
            "Query cache middleware enabled",
            extra={
                "ttl_seconds": cache_config.ttl_seconds,
                "cache_all_queries": cache_config.cache_all_queries,
            },
        )


async def bootstrap_cqrs(
    command_bus: CommandBus,
    query_bus: QueryBus,
    configure_middleware: bool = True,
    enable_resilience: bool = False,
    enable_query_cache: bool = True,
) -> None:
    """Bootstrap CQRS system by registering all handlers.

    This is the main entry point for CQRS handler registration.
    Call this function during application startup after database
    initialization.

    Handlers are registered with factory functions that create
    fresh repository instances per-call from the global database session.

    Args:
        command_bus: CommandBus instance.
        query_bus: QueryBus instance.
        configure_middleware: Whether to configure middleware (default: True).
        enable_resilience: Enable resilience middleware (default: False).
            See ADR-003 for rationale on why this is disabled by default.
        enable_query_cache: Enable query result caching (default: True).
    """
    logger.info("Bootstrapping CQRS handlers...")

    # Configure middleware first (outer layers)
    if configure_middleware:
        configure_cqrs_middleware(
            command_bus=command_bus,
            query_bus=query_bus,
            enable_resilience=enable_resilience,
            enable_observability=True,
            enable_query_cache=enable_query_cache,
        )

    # Register handlers (will be wrapped by middleware)
    await register_user_handlers(
        command_bus=command_bus,
        query_bus=query_bus,
    )

    logger.info("CQRS bootstrap complete")
