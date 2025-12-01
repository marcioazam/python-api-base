"""CSP generator with route-based policies.

**Feature: file-size-compliance-phase2, Task 2.4**
**Validates: Requirements 1.4, 5.1, 5.2, 5.3**
"""

import secrets

from .enums import CSPDirective, CSPKeyword
from .policy import CSPPolicy, RouteCSPConfig


class CSPGenerator:
    """Dynamic CSP generator with route-based policies."""

    def __init__(
        self,
        base_policy: CSPPolicy | None = None,
        nonce_length: int = 16,
    ) -> None:
        """Initialize CSP generator."""
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
        """Generate a cryptographically secure nonce."""
        return secrets.token_urlsafe(self._nonce_length)

    def add_route_config(self, config: RouteCSPConfig) -> None:
        """Add route-specific CSP configuration."""
        self._route_configs.append(config)

    def remove_route_config(self, pattern: str) -> bool:
        """Remove route configuration by pattern."""
        for i, config in enumerate(self._route_configs):
            if config.pattern == pattern:
                self._route_configs.pop(i)
                return True
        return False

    def _match_route(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern."""
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
        """Get CSP policy for a specific route."""
        policy = CSPPolicy(
            directives={k: v.copy() for k, v in self._base_policy.directives.items()},
            report_only=self._base_policy.report_only,
        )

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

        if include_nonce:
            policy.nonce = self.generate_nonce()

        return policy

    def get_headers(
        self,
        path: str,
        include_nonce: bool = True,
    ) -> dict[str, str]:
        """Get CSP headers for a route."""
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
