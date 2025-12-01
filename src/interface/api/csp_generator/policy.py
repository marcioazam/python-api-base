"""CSP policy models.

**Feature: file-size-compliance-phase2, Task 2.4**
**Validates: Requirements 1.4, 5.1, 5.2, 5.3**
"""

from dataclasses import dataclass, field

from .enums import CSPDirective


@dataclass
class CSPPolicy:
    """Content Security Policy configuration."""

    directives: dict[CSPDirective, list[str]] = field(default_factory=dict)
    report_only: bool = False
    nonce: str | None = None

    def add_source(self, directive: CSPDirective, source: str) -> "CSPPolicy":
        """Add a source to a directive."""
        if directive not in self.directives:
            self.directives[directive] = []
        if source not in self.directives[directive]:
            self.directives[directive].append(source)
        return self

    def remove_source(self, directive: CSPDirective, source: str) -> "CSPPolicy":
        """Remove a source from a directive."""
        if directive in self.directives and source in self.directives[directive]:
            self.directives[directive].remove(source)
        return self

    def set_directive(self, directive: CSPDirective, sources: list[str]) -> "CSPPolicy":
        """Set all sources for a directive."""
        self.directives[directive] = sources.copy()
        return self

    def merge(self, other: "CSPPolicy") -> "CSPPolicy":
        """Merge another policy into this one."""
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
        """Convert policy to CSP header value."""
        parts = []

        for directive, sources in self.directives.items():
            if not sources:
                if directive in (
                    CSPDirective.UPGRADE_INSECURE_REQUESTS,
                    CSPDirective.BLOCK_ALL_MIXED_CONTENT,
                ):
                    parts.append(directive.value)
            else:
                effective_sources = sources.copy()
                if self.nonce and directive in (
                    CSPDirective.SCRIPT_SRC,
                    CSPDirective.STYLE_SRC,
                ):
                    effective_sources.append(f"'nonce-{self.nonce}'")

                parts.append(f"{directive.value} {' '.join(effective_sources)}")

        return "; ".join(parts)

    def get_header_name(self) -> str:
        """Get the appropriate header name."""
        if self.report_only:
            return "Content-Security-Policy-Report-Only"
        return "Content-Security-Policy"


@dataclass
class RouteCSPConfig:
    """CSP configuration for a specific route pattern."""

    pattern: str
    policy: CSPPolicy
    override: bool = False
