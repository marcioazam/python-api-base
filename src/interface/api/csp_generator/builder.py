"""CSP policy builder.

**Feature: file-size-compliance-phase2, Task 2.4**
**Validates: Requirements 1.4, 5.1, 5.2, 5.3**
"""

from .enums import CSPDirective, CSPKeyword
from .policy import CSPPolicy


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
        """Build the CSP policy."""
        return self._policy


def create_strict_policy() -> CSPPolicy:
    """Create a strict CSP policy."""
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
    """Create a relaxed CSP policy for development."""
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
