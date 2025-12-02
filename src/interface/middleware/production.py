"""Production-ready middleware using generic infrastructure components.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 13, 16, 18, 19, 22**

Provides ready-to-use middleware for:
- Resilience (circuit breaker, retry, timeout)
- Multitenancy (tenant resolution and context)
- Feature flags (flag evaluation in requests)
- Audit logging (request/response audit trail)
"""

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from infrastructure.audit import (
    AuditAction,
    AuditRecord,
    AuditStore,
)
from infrastructure.feature_flags import (
    EvaluationContext,
    FeatureFlagEvaluator,
)
from infrastructure.multitenancy import (
    TenantContext,
    TenantInfo,
    TenantResolutionStrategy,
)
from infrastructure.resilience import CircuitBreaker, CircuitBreakerConfig, CircuitState

logger = logging.getLogger(__name__)


# =============================================================================
# Resilience Middleware
# =============================================================================


@dataclass
class ResilienceConfig:
    """Configuration for resilience middleware."""

    failure_threshold: int = 5
    timeout_seconds: float = 30.0
    enabled: bool = True


class ResilienceMiddleware(BaseHTTPMiddleware):
    """Middleware that applies circuit breaker pattern to requests.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 16.1**

    Usage:
        app.add_middleware(ResilienceMiddleware, config=ResilienceConfig())
    """

    def __init__(self, app: Any, config: ResilienceConfig | None = None) -> None:
        super().__init__(app)
        self._config = config or ResilienceConfig()
        self._circuit = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=self._config.failure_threshold,
                timeout_seconds=self._config.timeout_seconds,
            )
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request with circuit breaker protection."""
        if not self._config.enabled:
            return await call_next(request)

        # Check circuit state
        if not self._circuit.can_execute():
            logger.warning(
                f"Circuit breaker OPEN for {request.url.path}",
                extra={"path": request.url.path, "state": CircuitState.OPEN.value},
            )
            return Response(
                content='{"error": "Service temporarily unavailable"}',
                status_code=503,
                media_type="application/json",
            )

        try:
            response = await call_next(request)
            if response.status_code < 500:
                self._circuit.record_success()
            else:
                self._circuit.record_failure()
            return response
        except Exception as e:
            self._circuit.record_failure()
            logger.error(f"Request failed: {e}", exc_info=True)
            raise


# =============================================================================
# Multitenancy Middleware
# =============================================================================


@dataclass
class MultitenancyConfig:
    """Configuration for multitenancy middleware."""

    strategy: TenantResolutionStrategy = TenantResolutionStrategy.HEADER
    header_name: str = "X-Tenant-ID"
    required: bool = False
    default_tenant_id: str | None = None


class MultitenancyMiddleware(BaseHTTPMiddleware):
    """Middleware that resolves and sets tenant context.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 18.1**

    Usage:
        app.add_middleware(MultitenancyMiddleware, config=MultitenancyConfig())
    """

    def __init__(self, app: Any, config: MultitenancyConfig | None = None) -> None:
        super().__init__(app)
        self._config = config or MultitenancyConfig()
        self._context = TenantContext[str](
            strategy=self._config.strategy,
            header_name=self._config.header_name,
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request with tenant context."""
        # Resolve tenant ID from headers
        tenant_id = request.headers.get(self._config.header_name)

        if tenant_id is None:
            if self._config.required:
                return Response(
                    content='{"error": "Tenant ID required"}',
                    status_code=400,
                    media_type="application/json",
                )
            tenant_id = self._config.default_tenant_id

        # Set tenant context
        if tenant_id:
            tenant = TenantInfo[str](
                id=tenant_id,
                name=f"Tenant {tenant_id}",
            )
            TenantContext.set_current(tenant)
            logger.debug(f"Tenant context set: {tenant_id}")

        try:
            response = await call_next(request)
            return response
        finally:
            # Clear tenant context
            TenantContext.set_current(None)


# =============================================================================
# Feature Flag Middleware
# =============================================================================


class FeatureFlagMiddleware(BaseHTTPMiddleware):
    """Middleware that provides feature flag evaluation in request context.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 19.2**

    Usage:
        evaluator = FeatureFlagEvaluator()
        evaluator.register(FeatureFlag(key="new_api", ...))
        app.add_middleware(FeatureFlagMiddleware, evaluator=evaluator)
    """

    def __init__(self, app: Any, evaluator: FeatureFlagEvaluator[Any]) -> None:
        super().__init__(app)
        self._evaluator = evaluator

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request with feature flag context."""
        # Extract user ID from request (from auth header, JWT, etc.)
        user_id = request.headers.get("X-User-ID")

        # Create evaluation context
        context = EvaluationContext[dict](
            user_id=user_id,
            attributes={
                "path": request.url.path,
                "method": request.method,
            },
        )

        # Store evaluator and context in request state
        request.state.feature_flags = self._evaluator
        request.state.feature_context = context

        return await call_next(request)


def is_feature_enabled(request: Request, flag_key: str) -> bool:
    """Check if feature is enabled for current request.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 19.2**

    Usage in route handlers:
        @app.get("/items")
        async def list_items(request: Request):
            if is_feature_enabled(request, "new_items_api"):
                return new_items_response()
            return old_items_response()
    """
    evaluator = getattr(request.state, "feature_flags", None)
    context = getattr(request.state, "feature_context", None)

    if evaluator is None or context is None:
        return False

    return evaluator.is_enabled(flag_key, context)


# =============================================================================
# Audit Middleware
# =============================================================================


@dataclass
class AuditConfig:
    """Configuration for audit middleware."""

    enabled: bool = True
    log_request_body: bool = False
    log_response_body: bool = False
    exclude_paths: set[str] | None = None


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware that creates audit records for all requests.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 22.1, 22.4**

    Usage:
        store = InMemoryAuditStore()
        app.add_middleware(AuditMiddleware, store=store)
    """

    def __init__(
        self,
        app: Any,
        store: AuditStore[Any],
        config: AuditConfig | None = None,
    ) -> None:
        super().__init__(app)
        self._store = store
        self._config = config or AuditConfig()
        self._exclude = self._config.exclude_paths or {"/health", "/metrics", "/docs"}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request and create audit record."""
        if not self._config.enabled:
            return await call_next(request)

        # Skip excluded paths
        if request.url.path in self._exclude:
            return await call_next(request)

        # Get correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        user_id = request.headers.get("X-User-ID")

        # Map HTTP method to audit action
        action_map = {
            "GET": AuditAction.READ,
            "POST": AuditAction.CREATE,
            "PUT": AuditAction.UPDATE,
            "PATCH": AuditAction.UPDATE,
            "DELETE": AuditAction.DELETE,
        }
        action = action_map.get(request.method, AuditAction.READ)

        start_time = time.time()

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Create audit record
            record = AuditRecord[dict](
                entity_type="http_request",
                entity_id=request.url.path,
                action=action,
                user_id=user_id,
                correlation_id=correlation_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                metadata={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            await self._store.save(record)
            logger.debug(f"Audit record created: {record.id}")

            return response

        except Exception as e:
            # Create error audit record
            record = AuditRecord[dict](
                entity_type="http_request",
                entity_id=request.url.path,
                action=action,
                user_id=user_id,
                correlation_id=correlation_id,
                metadata={
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                },
            )
            await self._store.save(record)
            raise


# =============================================================================
# Combined Production Middleware Stack
# =============================================================================


def setup_production_middleware(
    app: Any,
    *,
    resilience_config: ResilienceConfig | None = None,
    multitenancy_config: MultitenancyConfig | None = None,
    feature_evaluator: FeatureFlagEvaluator[Any] | None = None,
    audit_store: AuditStore[Any] | None = None,
    audit_config: AuditConfig | None = None,
) -> None:
    """Setup complete production middleware stack.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 13, 16, 18, 19, 22**

    Usage:
        from interface.middleware.production import setup_production_middleware

        app = FastAPI()
        setup_production_middleware(
            app,
            resilience_config=ResilienceConfig(failure_threshold=10),
            multitenancy_config=MultitenancyConfig(required=True),
            audit_store=InMemoryAuditStore(),
        )
    """
    # Order matters: audit first (outermost), then resilience,
    # then tenant, then features
    if audit_store:
        app.add_middleware(
            AuditMiddleware,
            store=audit_store,
            config=audit_config,
        )
        logger.info("Audit middleware enabled")

    if resilience_config:
        app.add_middleware(ResilienceMiddleware, config=resilience_config)
        logger.info("Resilience middleware enabled")

    if multitenancy_config:
        app.add_middleware(MultitenancyMiddleware, config=multitenancy_config)
        logger.info("Multitenancy middleware enabled")

    if feature_evaluator:
        app.add_middleware(FeatureFlagMiddleware, evaluator=feature_evaluator)
        logger.info("Feature flag middleware enabled")
