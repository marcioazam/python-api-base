"""Content Security Policy (CSP) generator with dynamic nonce support.

**Feature: api-architecture-analysis, Task 11.8: CSP Generator**
**Validates: Requirements 5.3**

Provides dynamic CSP generation based on routes with nonce support for inline scripts.
"""

import secrets
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CSPDirective(str, Enum):
    """CSP directive names."""

    DEFAULT_SRC = "default-src"
    SCRIPT_SRC = "script-src"
    STYLE_SRC = "style-src"
    IMG_SRC = "img-src"
    FONT_SRC = "font-src"
    CONNECT_SRC = "connect-src"
    MEDIA_SRC = "media-src"
    OBJECT_SRC = "object-src"
    FRAME_SRC = "frame-src"
    FRAME_ANCESTORS = "frame-ancestors"
    BASE_URI = "base-uri"
    FORM_ACTION = "form-action"
    WORKER_SRC = "worker-src"
    MANIFEST_SRC = "manifest-src"
    REPORT_URI = "report-uri"
    REPORT_TO = "report-to"
    UPGRADE_INSECURE_REQUESTS = "upgrade-insecure-requests"
    BLOCK_ALL_MIXED_CONTENT = "block-all-mixed-content"


class CSPKeyword(str, Enum):
    """CSP source keywords."""

    SELF = "'self'"
    NONE = "'none'"
    UNSAFE_INLINE = "'unsafe-inline'"
    UNSAFE_EVAL = "'unsafe-eval'"
    STRICT_DYNAMIC = "'strict-dynamic'"
    UNSAFE_HASHES = "'unsafe-hashes'"
    WASM_UNSAFE_EVAL = "'wasm-unsafe-eval'"


@dataclass
class CSPPolicy:
    """Content Security Policy configuration.

    Attributes:
        directives: Map of directive to allowed sources.
        report_only: Whether to use report-only mode.
        nonce: Generated nonce for inline scripts/styles.
    """

    directives: dict[CSPDirective, list[str]] = field(default_factory=dict)
    report_only: bool = False
    nonce: str | None = None

    def add_source(self, directive: CSPDirective, source: str) -> "CSPPolicy":
        """Add a source to a directive.

        Args:
            directive: CSP directive.
            source: Source to add.

        Returns:
            Self for chaining.
        """
        if directive not in self.directives:
            self.directives[directive] = []
        if source not in self.directives[directive]:
            self.directives[directive].append(source)
        return self

    def remove_source(self, directive: CSPDirective, source: str) -> "CSPPolicy":
        """Remove a source from a directive.

        Args:
            directive: CSP directive.
            source: Source to remove.

        Returns:
            Self for chaining.
        """
        if directive in self.directives and source in self.directives[directive]:
            self.directives[directive].remove(source)
        return self

    def set_directive(self, directive: CSPDirective, sources: list[str]) -> "CSPPolicy":
        """Set all sources for a directive.

        Args:
            directive: CSP directive.
            sources: List of sources.

        Returns:
            Self for chaining.
        """
        self.directives[directive] = sources.copy()
        return self

    def merge(self, other: "CSPPolicy") -> "CSPPolicy":
        """Merge another policy into this one.

        Args:
            other: Policy to merge.

        Returns:
            New merged policy.
        """
        merged = CSPPolicy(
            directives={k: v.copy() for k, v in self.directives.items()},
            report_only=self.report_only,
            nonce=self.nonce,
        )

        for directive, sources in other.directives.items():
            if directive not in merged.directives:
                merged.directives[directive] = []
            for source in sources:
                if source not in merged.directives[directive]:
                    merged.directives[directive].append(source)

        return merged

    def to_header_value(self) -> str:
        """Convert policy to CSP header value.

        Returns:
            CSP header string.
        """
        parts = []

        for directive, sources in self.directives.items():
            if not sources:
                # Directives like upgrade-insecure-requests have no sources
                if directive in (
                    CSPDirective.UPGRADE_INSECURE_REQUESTS,
                    CSPDirective.BLOCK_ALL_MIXED_CONTENT,
                ):
                    parts.append(directive.value)
            else:
                # Add nonce to script-src and style-src if present
                effective_sources = sources.copy()
                if self.nonce and directive in (
                    CSPDirective.SCRIPT_SRC,
                    CSPDirective.STYLE_SRC,
                ):
                    effective_sources.append(f"'nonce-{self.nonce}'")

                parts.append(f"{directive.value} {' '.join(effective_sources)}")

        return "; ".join(parts)

    def get_header_name(self) -> str:
        """Get the appropriate header name.

        Returns:
            Header name based on report_only setting.
        """
        if self.report_only:
            return "Content-Security-Policy-Report-Only"
        return "Content-Security-Policy"


@dataclass
class RouteCSPConfig:
    """CSP configuration for a specific route pattern.

    Attributes:
        pattern: Route pattern (supports wildcards).
        policy: CSP policy for this route.
        override: Whether to override base policy or merge.
    """

    pattern: str
    policy: CSPPolicy
    override: bool = False


class CSPGenerator:
    """Dynamic CSP generator with route-based policies.

    Generates Content Security Policy headers with support for:
    - Base policy for all routes
    - Route-specific policies
    - Dynamic nonce generation for inline scripts
    - Report-only mode for testing
    """

    def __init__(
        self,
        base_policy: CSPPolicy | None = None,
        nonce_length: int = 16,
    ) -> None:
        """Initialize CSP generator.

        Args:
            base_policy: Base policy applied to all routes.
            nonce_length: Length of generated nonces in bytes.
        """
        self._base_policy = base_policy or self._default_policy()
        self._route_configs: list[RouteCSPConfig] = []
        self._nonce_length = nonce_length

    @staticmethod
    def _default_policy() -> CSPPolicy:
        """Create default restrictive policy."""
        return CSPPolicy(
            directives={
                CSPDirective.DEFAULT_SRC: [CSPKeyword.SELF.value],
                CSPDirective.SCRIPT_SRC: [CSPKeyword.SELF.value],
                CSPDirective.STYLE_SRC: [CSPKeyword.SELF.value],
                CSPDirective.IMG_SRC: [CSPKeyword.SELF.value, "data:"],
                CSPDirective.FONT_SRC: [CSPKeyword.SELF.value],
                CSPDirective.CONNECT_SRC: [CSPKeyword.SELF.value],
                CSPDirective.FRAME_ANCESTORS: [CSPKeyword.NONE.value],
                CSPDirective.BASE_URI: [CSPKeyword.SELF.value],
                CSPDirective.FORM_ACTION: [CSPKeyword.SELF.value],
                CSPDirective.OBJECT_SRC: [CSPKeyword.NONE.value],
            }
        )

    def generate_nonce(self) -> str:
        """Generate a cryptographically secure nonce.

        Returns:
            Base64-encoded nonce string.
        """
        return secrets.token_urlsafe(self._nonce_length)

    def add_route_config(self, config: RouteCSPConfig) -> None:
        """Add route-specific CSP configuration.

        Args:
            config: Route CSP configuration.
        """
        self._route_configs.append(config)

    def remove_route_config(self, pattern: str) -> bool:
        """Remove route configuration by pattern.

        Args:
            pattern: Route pattern to remove.

        Returns:
            True if removed, False if not found.
        """
        for i, config in enumerate(self._route_configs):
            if config.pattern == pattern:
                self._route_configs.pop(i)
                return True
        return False

    def _match_route(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern.

        Supports:
        - Exact match: /api/users
        - Wildcard suffix: /api/*
        - Wildcard prefix: */users
        - Full wildcard: *

        Args:
            path: Request path.
            pattern: Route pattern.

        Returns:
            True if path matches pattern.
        """
        if pattern == "*":
            return True

        if pattern.endswith("/*"):
            prefix = pattern[:-2]
            return path.startswith(prefix)

        if pattern.startswith("*/"):
            suffix = pattern[2:]
            return path.endswith(suffix)

        return path == pattern

    def get_policy_for_route(
        self,
        path: str,
        include_nonce: bool = True,
    ) -> CSPPolicy:
        """Get CSP policy for a specific route.

        Args:
            path: Request path.
            include_nonce: Whether to generate and include nonce.

        Returns:
            CSP policy for the route.
        """
        # Start with base policy
        policy = CSPPolicy(
            directives={k: v.copy() for k, v in self._base_policy.directives.items()},
            report_only=self._base_policy.report_only,
        )

        # Apply matching route configs
        for config in self._route_configs:
            if self._match_route(path, config.pattern):
                if config.override:
                    policy = CSPPolicy(
                        directives={
                            k: v.copy() for k, v in config.policy.directives.items()
                        },
                        report_only=config.policy.report_only,
                    )
                else:
                    policy = policy.merge(config.policy)

        # Generate nonce if requested
        if include_nonce:
            policy.nonce = self.generate_nonce()

        return policy

    def get_headers(
        self,
        path: str,
        include_nonce: bool = True,
    ) -> dict[str, str]:
        """Get CSP headers for a route.

        Args:
            path: Request path.
            include_nonce: Whether to include nonce.

        Returns:
            Dictionary with header name and value.
        """
        policy = self.get_policy_for_route(path, include_nonce)
        return {policy.get_header_name(): policy.to_header_value()}

    @property
    def base_policy(self) -> CSPPolicy:
        """Get base policy."""
        return self._base_policy

    @base_policy.setter
    def base_policy(self, policy: CSPPolicy) -> None:
        """Set base policy."""
        self._base_policy = policy


class CSPBuilder:
    """Fluent builder for CSP policies."""

    def __init__(self) -> None:
        self._policy = CSPPolicy()

    def default_src(self, *sources: str) -> "CSPBuilder":
        """Set default-src directive."""
        self._policy.set_directive(CSPDirective.DEFAULT_SRC, list(sources))
        return self

    def script_src(self, *sources: str) -> "CSPBuilder":
        """Set script-src directive."""
        self._policy.set_directive(CSPDirective.SCRIPT_SRC, list(sources))
        return self

    def style_src(self, *sources: str) -> "CSPBuilder":
        """Set style-src directive."""
        self._policy.set_directive(CSPDirective.STYLE_SRC, list(sources))
        return self

    def img_src(self, *sources: str) -> "CSPBuilder":
        """Set img-src directive."""
        self._policy.set_directive(CSPDirective.IMG_SRC, list(sources))
        return self

    def font_src(self, *sources: str) -> "CSPBuilder":
        """Set font-src directive."""
        self._policy.set_directive(CSPDirective.FONT_SRC, list(sources))
        return self

    def connect_src(self, *sources: str) -> "CSPBuilder":
        """Set connect-src directive."""
        self._policy.set_directive(CSPDirective.CONNECT_SRC, list(sources))
        return self

    def frame_ancestors(self, *sources: str) -> "CSPBuilder":
        """Set frame-ancestors directive."""
        self._policy.set_directive(CSPDirective.FRAME_ANCESTORS, list(sources))
        return self

    def base_uri(self, *sources: str) -> "CSPBuilder":
        """Set base-uri directive."""
        self._policy.set_directive(CSPDirective.BASE_URI, list(sources))
        return self

    def form_action(self, *sources: str) -> "CSPBuilder":
        """Set form-action directive."""
        self._policy.set_directive(CSPDirective.FORM_ACTION, list(sources))
        return self

    def object_src(self, *sources: str) -> "CSPBuilder":
        """Set object-src directive."""
        self._policy.set_directive(CSPDirective.OBJECT_SRC, list(sources))
        return self

    def report_uri(self, uri: str) -> "CSPBuilder":
        """Set report-uri directive."""
        self._policy.set_directive(CSPDirective.REPORT_URI, [uri])
        return self

    def upgrade_insecure_requests(self) -> "CSPBuilder":
        """Add upgrade-insecure-requests directive."""
        self._policy.set_directive(CSPDirective.UPGRADE_INSECURE_REQUESTS, [])
        return self

    def report_only(self, enabled: bool = True) -> "CSPBuilder":
        """Set report-only mode."""
        self._policy.report_only = enabled
        return self

    def build(self) -> CSPPolicy:
        """Build the CSP policy.

        Returns:
            Configured CSP policy.
        """
        return self._policy


def create_strict_policy() -> CSPPolicy:
    """Create a strict CSP policy.

    Returns:
        Strict CSP policy suitable for security-sensitive applications.
    """
    return (
        CSPBuilder()
        .default_src(CSPKeyword.NONE.value)
        .script_src(CSPKeyword.SELF.value, CSPKeyword.STRICT_DYNAMIC.value)
        .style_src(CSPKeyword.SELF.value)
        .img_src(CSPKeyword.SELF.value, "data:")
        .font_src(CSPKeyword.SELF.value)
        .connect_src(CSPKeyword.SELF.value)
        .frame_ancestors(CSPKeyword.NONE.value)
        .base_uri(CSPKeyword.SELF.value)
        .form_action(CSPKeyword.SELF.value)
        .object_src(CSPKeyword.NONE.value)
        .upgrade_insecure_requests()
        .build()
    )


def create_relaxed_policy() -> CSPPolicy:
    """Create a relaxed CSP policy for development.

    Returns:
        Relaxed CSP policy suitable for development environments.
    """
    return (
        CSPBuilder()
        .default_src(CSPKeyword.SELF.value)
        .script_src(CSPKeyword.SELF.value, CSPKeyword.UNSAFE_INLINE.value, CSPKeyword.UNSAFE_EVAL.value)
        .style_src(CSPKeyword.SELF.value, CSPKeyword.UNSAFE_INLINE.value)
        .img_src(CSPKeyword.SELF.value, "data:", "blob:", "*")
        .font_src(CSPKeyword.SELF.value, "data:")
        .connect_src(CSPKeyword.SELF.value, "*")
        .frame_ancestors(CSPKeyword.SELF.value)
        .build()
    )
