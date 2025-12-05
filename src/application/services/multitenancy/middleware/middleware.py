"""Tenant middleware for ASGI applications.

**Feature: enterprise-features-2025**
**Validates: Requirements 7.3**
**Split from: service.py for SRP compliance**
"""

import functools
import logging
import re
from typing import Any, Final

from application.services.multitenancy.models import (
    TenantContext,
    get_current_tenant,
)

logger = logging.getLogger(__name__)

# Security constants for tenant ID validation
TENANT_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
TENANT_ID_MAX_LENGTH: Final[int] = 64


class TenantMiddleware:
    """ASGI middleware for tenant context extraction.

    Extracts tenant ID from request headers or path and sets
    it in the context for downstream use.

    Usage:
        app.add_middleware(
            TenantMiddleware,
            header_name="X-Tenant-ID",
        )
    """

    def __init__(
        self,
        app: Any,
        header_name: str = "X-Tenant-ID",
        path_param: str | None = None,
    ) -> None:
        """Initialize middleware.

        Args:
            app: ASGI application.
            header_name: Header name for tenant ID.
            path_param: Optional path parameter name for tenant ID.
        """
        self.app = app
        self.header_name = header_name.lower()
        self.path_param = path_param

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        """Process request and set tenant context."""
        if scope["type"] == "http":
            tenant_id = self._extract_tenant_id(scope)
            if tenant_id:
                async with TenantContext(tenant_id):
                    await self.app(scope, receive, send)
                return

        await self.app(scope, receive, send)

    def _extract_tenant_id(self, scope: dict) -> str | None:
        """Extract and sanitize tenant ID from request."""
        tenant_id: str | None = None

        # Try header first
        headers = dict(scope.get("headers", []))
        header_value = headers.get(self.header_name.encode())
        if header_value:
            tenant_id = header_value.decode()

        # Try path parameter if header not found
        if tenant_id is None and self.path_param:
            path_params = scope.get("path_params", {})
            if self.path_param in path_params:
                tenant_id = str(path_params[self.path_param])

        # Sanitize tenant ID before returning
        if tenant_id is not None:
            return self._sanitize_tenant_id(tenant_id)

        return None

    def _sanitize_tenant_id(self, tenant_id: str) -> str | None:
        """Sanitize tenant ID to prevent injection attacks.

        Validates tenant ID against a strict pattern to prevent:
        - SQL injection
        - Path traversal
        - Header injection
        - Empty/whitespace-only bypass

        **Feature: application-layer-code-review-fixes**
        **Validates: Requirements F-01**
        """
        # Strip whitespace first to handle " valid " -> "valid"
        tenant_id = tenant_id.strip()

        # Reject empty after strip (handles "" and "   ")
        if not tenant_id:
            logger.warning(
                "Tenant ID rejected: empty or whitespace-only",
                extra={
                    "operation": "TENANT_VALIDATION",
                    "reason": "EMPTY_OR_WHITESPACE",
                },
            )
            return None

        if len(tenant_id) > TENANT_ID_MAX_LENGTH:
            logger.warning(
                "Tenant ID rejected: exceeds max length",
                extra={
                    "operation": "TENANT_VALIDATION",
                    "reason": "LENGTH_EXCEEDED",
                },
            )
            return None

        if not TENANT_ID_PATTERN.match(tenant_id):
            logger.warning(
                "Tenant ID rejected: invalid characters",
                extra={
                    "operation": "TENANT_VALIDATION",
                    "reason": "INVALID_CHARS",
                },
            )
            return None

        return tenant_id


def require_tenant(func: Any) -> Any:
    """Decorator to require tenant context.

    Raises ValueError if no tenant is set in context.

    Usage:
        @require_tenant
        async def get_items():
            tenant = get_current_tenant()
            # tenant is guaranteed to be set
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if get_current_tenant() is None:
            raise ValueError("Tenant context required but not set")
        return await func(*args, **kwargs)

    return wrapper
