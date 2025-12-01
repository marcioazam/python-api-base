"""Advanced CORS Configuration - Dynamic CORS management.

**Feature: api-architecture-analysis, Priority 11.2: Advanced CORS**
**Validates: Requirements 5.3**

Provides:
- CORSManager with dynamic origins
- Per-route CORS policies
- Origin validation and whitelisting
- Preflight request handling
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from collections.abc import Callable


class CORSCredentials(str, Enum):
    """Credentials mode for CORS."""

    INCLUDE = "include"
    OMIT = "omit"
    SAME_ORIGIN = "same-origin"


@dataclass
class CORSPolicy:
    """CORS policy configuration."""

    allow_origins: list[str] = field(default_factory=lambda: ["*"])
    allow_methods: list[str] = field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    )
    allow_headers: list[str] = field(default_factory=lambda: ["*"])
    expose_headers: list[str] = field(default_factory=list)
    allow_credentials: bool = False
    max_age: int = 86400  # 24 hours

    def allows_origin(self, origin: str) -> bool:
        """Check if origin is allowed."""
        if "*" in self.allow_origins:
            return True
        return origin in self.allow_origins

    def allows_method(self, method: str) -> bool:
        """Check if method is allowed."""
        if "*" in self.allow_methods:
            return True
        return method.upper() in [m.upper() for m in self.allow_methods]

    def to_headers(self, origin: str | None = None) -> dict[str, str]:
        """Convert policy to CORS headers."""
        headers: dict[str, str] = {}

        # Access-Control-Allow-Origin
        if origin and self.allows_origin(origin):
            if self.allow_credentials:
                headers["Access-Control-Allow-Origin"] = origin
            elif "*" in self.allow_origins:
                headers["Access-Control-Allow-Origin"] = "*"
            else:
                headers["Access-Control-Allow-Origin"] = origin

        # Access-Control-Allow-Methods
        if self.allow_methods:
            headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)

        # Access-Control-Allow-Headers
        if self.allow_headers:
            if "*" in self.allow_headers:
                headers["Access-Control-Allow-Headers"] = "*"
            else:
                headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)

        # Access-Control-Expose-Headers
        if self.expose_headers:
            headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)

        # Access-Control-Allow-Credentials
        if self.allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"

        # Access-Control-Max-Age
        if self.max_age > 0:
            headers["Access-Control-Max-Age"] = str(self.max_age)

        return headers


@dataclass
class RoutePolicy:
    """CORS policy for a specific route pattern."""

    pattern: str
    policy: CORSPolicy
    priority: int = 0
    _compiled: re.Pattern | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Compile pattern."""
        try:
            self._compiled = re.compile(self.pattern)
        except re.error:
            self._compiled = None

    def matches(self, path: str) -> bool:
        """Check if path matches this route."""
        if self._compiled is None:
            return False
        return bool(self._compiled.match(path))


@dataclass
class CORSRequest:
    """Normalized CORS request."""

    origin: str | None
    method: str
    path: str
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def is_preflight(self) -> bool:
        """Check if this is a preflight request."""
        return self.method.upper() == "OPTIONS" and self.origin is not None

    @property
    def requested_method(self) -> str | None:
        """Get requested method from preflight."""
        return self.headers.get("Access-Control-Request-Method")

    @property
    def requested_headers(self) -> list[str]:
        """Get requested headers from preflight."""
        header = self.headers.get("Access-Control-Request-Headers", "")
        if not header:
            return []
        return [h.strip() for h in header.split(",")]


@dataclass
class CORSResponse:
    """CORS response with headers."""

    allowed: bool
    headers: dict[str, str] = field(default_factory=dict)
    policy_used: CORSPolicy | None = None
    is_preflight: bool = False


class CORSManager:
    """Advanced CORS manager with dynamic configuration."""

    def __init__(self, default_policy: CORSPolicy | None = None) -> None:
        """Initialize CORS manager."""
        self._default_policy = default_policy or CORSPolicy()
        self._route_policies: list[RoutePolicy] = []
        self._origin_validators: list[Callable[[str], bool]] = []
        self._whitelist: set[str] = set()
        self._blacklist: set[str] = set()
        self._pattern_whitelist: list[re.Pattern] = []

    def set_default_policy(self, policy: CORSPolicy) -> "CORSManager":
        """Set default CORS policy."""
        self._default_policy = policy
        return self

    def add_route_policy(
        self,
        pattern: str,
        policy: CORSPolicy,
        priority: int = 0,
    ) -> "CORSManager":
        """Add route-specific CORS policy."""
        route_policy = RoutePolicy(pattern=pattern, policy=policy, priority=priority)
        self._route_policies.append(route_policy)
        # Sort by priority (higher first)
        self._route_policies.sort(key=lambda x: x.priority, reverse=True)
        return self

    def remove_route_policy(self, pattern: str) -> bool:
        """Remove route policy by pattern."""
        initial_len = len(self._route_policies)
        self._route_policies = [rp for rp in self._route_policies if rp.pattern != pattern]
        return len(self._route_policies) < initial_len

    def add_origin_validator(
        self,
        validator: Callable[[str], bool],
    ) -> "CORSManager":
        """Add custom origin validator."""
        self._origin_validators.append(validator)
        return self

    def whitelist_origin(self, origin: str) -> "CORSManager":
        """Add origin to whitelist."""
        self._whitelist.add(origin)
        return self

    def blacklist_origin(self, origin: str) -> "CORSManager":
        """Add origin to blacklist."""
        self._blacklist.add(origin)
        return self

    def whitelist_pattern(self, pattern: str) -> "CORSManager":
        """Add origin pattern to whitelist."""
        try:
            compiled = re.compile(pattern)
            self._pattern_whitelist.append(compiled)
        except re.error:
            pass
        return self

    def is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed."""
        # Check blacklist first
        if origin in self._blacklist:
            return False

        # Check explicit whitelist
        if origin in self._whitelist:
            return True

        # Check pattern whitelist
        for pattern in self._pattern_whitelist:
            if pattern.match(origin):
                return True

        # Check custom validators
        for validator in self._origin_validators:
            if validator(origin):
                return True

        # Check default policy
        return self._default_policy.allows_origin(origin)

    def get_policy_for_path(self, path: str) -> CORSPolicy:
        """Get CORS policy for a specific path."""
        for route_policy in self._route_policies:
            if route_policy.matches(path):
                return route_policy.policy
        return self._default_policy

    def handle_request(self, request: CORSRequest) -> CORSResponse:
        """Handle CORS request and return response."""
        # No origin = not a CORS request
        if not request.origin:
            return CORSResponse(allowed=True)

        # Check if origin is allowed
        if not self.is_origin_allowed(request.origin):
            return CORSResponse(allowed=False)

        # Get policy for this path
        policy = self.get_policy_for_path(request.path)

        # Handle preflight
        if request.is_preflight:
            return self._handle_preflight(request, policy)

        # Handle simple/actual request
        return self._handle_actual_request(request, policy)

    def _handle_preflight(
        self,
        request: CORSRequest,
        policy: CORSPolicy,
    ) -> CORSResponse:
        """Handle preflight OPTIONS request."""
        # Check requested method
        requested_method = request.requested_method
        if requested_method and not policy.allows_method(requested_method):
            return CORSResponse(
                allowed=False,
                is_preflight=True,
            )

        # Check requested headers
        requested_headers = request.requested_headers
        if requested_headers and "*" not in policy.allow_headers:
            for header in requested_headers:
                if header.lower() not in [h.lower() for h in policy.allow_headers]:
                    return CORSResponse(
                        allowed=False,
                        is_preflight=True,
                    )

        # Generate response headers
        headers = policy.to_headers(request.origin)

        return CORSResponse(
            allowed=True,
            headers=headers,
            policy_used=policy,
            is_preflight=True,
        )

    def _handle_actual_request(
        self,
        request: CORSRequest,
        policy: CORSPolicy,
    ) -> CORSResponse:
        """Handle actual CORS request."""
        # Check method
        if not policy.allows_method(request.method):
            return CORSResponse(allowed=False)

        # Generate response headers
        headers = policy.to_headers(request.origin)

        return CORSResponse(
            allowed=True,
            headers=headers,
            policy_used=policy,
            is_preflight=False,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get CORS manager statistics."""
        return {
            "route_policies": len(self._route_policies),
            "whitelist_size": len(self._whitelist),
            "blacklist_size": len(self._blacklist),
            "pattern_whitelist_size": len(self._pattern_whitelist),
            "custom_validators": len(self._origin_validators),
        }


def create_cors_manager(
    allow_origins: list[str] | None = None,
    allow_credentials: bool = False,
) -> CORSManager:
    """Factory function to create CORS manager."""
    policy = CORSPolicy(
        allow_origins=allow_origins or ["*"],
        allow_credentials=allow_credentials,
    )
    return CORSManager(default_policy=policy)


def create_strict_cors_policy(
    origins: list[str],
    methods: list[str] | None = None,
) -> CORSPolicy:
    """Create a strict CORS policy."""
    return CORSPolicy(
        allow_origins=origins,
        allow_methods=methods or ["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
        allow_credentials=True,
        max_age=3600,
    )


def create_permissive_cors_policy() -> CORSPolicy:
    """Create a permissive CORS policy for development."""
    return CORSPolicy(
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
        max_age=86400,
    )
