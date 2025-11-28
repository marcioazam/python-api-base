"""Property-based tests for CSP generator.

**Feature: api-architecture-analysis, Task 11.8: CSP Generator**
**Validates: Requirements 5.3**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from my_api.shared.csp_generator import (
    CSPBuilder,
    CSPDirective,
    CSPGenerator,
    CSPKeyword,
    CSPPolicy,
    RouteCSPConfig,
    create_relaxed_policy,
    create_strict_policy,
)


# =============================================================================
# Strategies
# =============================================================================

@st.composite
def csp_source_strategy(draw: st.DrawFn) -> str:
    """Generate valid CSP sources."""
    return draw(st.one_of(
        st.sampled_from([k.value for k in CSPKeyword]),
        st.just("https://example.com"),
        st.just("https://*.example.com"),
        st.just("data:"),
        st.just("blob:"),
    ))


@st.composite
def path_strategy(draw: st.DrawFn) -> str:
    """Generate URL paths."""
    segments = draw(st.lists(
        st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-"),
        min_size=1,
        max_size=5,
    ))
    return "/" + "/".join(segments)


@st.composite
def route_pattern_strategy(draw: st.DrawFn) -> str:
    """Generate route patterns."""
    return draw(st.one_of(
        path_strategy(),
        st.just("/api/*"),
        st.just("*/users"),
        st.just("*"),
    ))


# =============================================================================
# Property Tests - CSP Policy
# =============================================================================

class TestCSPPolicyProperties:
    """Property tests for CSP policy."""

    @given(
        directive=st.sampled_from(list(CSPDirective)),
        source=csp_source_strategy(),
    )
    @settings(max_examples=100)
    def test_add_source_adds_to_directive(
        self,
        directive: CSPDirective,
        source: str,
    ) -> None:
        """**Property 1: Add source adds to directive**

        *For any* directive and source, adding should include the source
        in that directive's list.

        **Validates: Requirements 5.3**
        """
        policy = CSPPolicy()
        policy.add_source(directive, source)

        assert directive in policy.directives
        assert source in policy.directives[directive]

    @given(
        directive=st.sampled_from(list(CSPDirective)),
        source=csp_source_strategy(),
    )
    @settings(max_examples=100)
    def test_add_source_idempotent(
        self,
        directive: CSPDirective,
        source: str,
    ) -> None:
        """**Property 2: Add source is idempotent**

        *For any* directive and source, adding the same source twice
        should not create duplicates.

        **Validates: Requirements 5.3**
        """
        policy = CSPPolicy()
        policy.add_source(directive, source)
        policy.add_source(directive, source)

        assert policy.directives[directive].count(source) == 1

    @given(
        directive=st.sampled_from(list(CSPDirective)),
        source=csp_source_strategy(),
    )
    @settings(max_examples=100)
    def test_remove_source_removes_from_directive(
        self,
        directive: CSPDirective,
        source: str,
    ) -> None:
        """**Property 3: Remove source removes from directive**

        *For any* added source, removing it should make it absent.

        **Validates: Requirements 5.3**
        """
        policy = CSPPolicy()
        policy.add_source(directive, source)
        policy.remove_source(directive, source)

        assert source not in policy.directives.get(directive, [])

    @given(
        directive=st.sampled_from(list(CSPDirective)),
        sources=st.lists(csp_source_strategy(), min_size=1, max_size=5),
    )
    @settings(max_examples=100)
    def test_set_directive_replaces_sources(
        self,
        directive: CSPDirective,
        sources: list[str],
    ) -> None:
        """**Property 4: Set directive replaces all sources**

        *For any* directive and sources, set_directive should replace
        all existing sources.

        **Validates: Requirements 5.3**
        """
        policy = CSPPolicy()
        policy.add_source(directive, "old_source")
        policy.set_directive(directive, sources)

        assert "old_source" not in policy.directives[directive]
        for source in sources:
            assert source in policy.directives[directive]

    @given(
        directive1=st.sampled_from(list(CSPDirective)),
        directive2=st.sampled_from(list(CSPDirective)),
        source1=csp_source_strategy(),
        source2=csp_source_strategy(),
    )
    @settings(max_examples=100)
    def test_merge_combines_policies(
        self,
        directive1: CSPDirective,
        directive2: CSPDirective,
        source1: str,
        source2: str,
    ) -> None:
        """**Property 5: Merge combines policies**

        *For any* two policies, merging should include sources from both.

        **Validates: Requirements 5.3**
        """
        policy1 = CSPPolicy()
        policy1.add_source(directive1, source1)

        policy2 = CSPPolicy()
        policy2.add_source(directive2, source2)

        merged = policy1.merge(policy2)

        assert source1 in merged.directives.get(directive1, [])
        assert source2 in merged.directives.get(directive2, [])


# =============================================================================
# Property Tests - Header Generation
# =============================================================================

class TestCSPHeaderProperties:
    """Property tests for CSP header generation."""

    @given(
        directive=st.sampled_from([
            CSPDirective.DEFAULT_SRC,
            CSPDirective.SCRIPT_SRC,
            CSPDirective.STYLE_SRC,
        ]),
        source=csp_source_strategy(),
    )
    @settings(max_examples=100)
    def test_header_contains_directive(
        self,
        directive: CSPDirective,
        source: str,
    ) -> None:
        """**Property 6: Header contains directive**

        *For any* policy with a directive, the header should contain
        that directive name.

        **Validates: Requirements 5.3**
        """
        policy = CSPPolicy()
        policy.add_source(directive, source)
        header = policy.to_header_value()

        assert directive.value in header

    @given(
        directive=st.sampled_from([
            CSPDirective.DEFAULT_SRC,
            CSPDirective.SCRIPT_SRC,
        ]),
        source=csp_source_strategy(),
    )
    @settings(max_examples=100)
    def test_header_contains_source(
        self,
        directive: CSPDirective,
        source: str,
    ) -> None:
        """**Property 7: Header contains source**

        *For any* policy with a source, the header should contain
        that source value.

        **Validates: Requirements 5.3**
        """
        policy = CSPPolicy()
        policy.add_source(directive, source)
        header = policy.to_header_value()

        assert source in header

    def test_report_only_header_name(self) -> None:
        """**Property 8: Report-only uses correct header name**

        When report_only is True, header name should be
        Content-Security-Policy-Report-Only.

        **Validates: Requirements 5.3**
        """
        policy = CSPPolicy(report_only=True)
        assert policy.get_header_name() == "Content-Security-Policy-Report-Only"

        policy.report_only = False
        assert policy.get_header_name() == "Content-Security-Policy"

    @given(nonce=st.text(min_size=16, max_size=32, alphabet="abcdefghijklmnopqrstuvwxyz0123456789"))
    @settings(max_examples=100)
    def test_nonce_included_in_script_src(self, nonce: str) -> None:
        """**Property 9: Nonce included in script-src**

        *For any* policy with nonce, script-src should include the nonce.

        **Validates: Requirements 5.3**
        """
        policy = CSPPolicy(nonce=nonce)
        policy.add_source(CSPDirective.SCRIPT_SRC, CSPKeyword.SELF.value)
        header = policy.to_header_value()

        assert f"'nonce-{nonce}'" in header


# =============================================================================
# Property Tests - CSP Generator
# =============================================================================

class TestCSPGeneratorProperties:
    """Property tests for CSP generator."""

    @given(path=path_strategy())
    @settings(max_examples=100)
    def test_generator_produces_valid_policy(self, path: str) -> None:
        """**Property 10: Generator produces valid policy**

        *For any* path, generator should produce a valid CSP policy.

        **Validates: Requirements 5.3**
        """
        generator = CSPGenerator()
        policy = generator.get_policy_for_route(path)

        assert policy is not None
        assert isinstance(policy, CSPPolicy)
        assert len(policy.directives) > 0

    @given(path=path_strategy())
    @settings(max_examples=100)
    def test_generator_includes_nonce(self, path: str) -> None:
        """**Property 11: Generator includes nonce when requested**

        *For any* path with include_nonce=True, policy should have nonce.

        **Validates: Requirements 5.3**
        """
        generator = CSPGenerator()
        policy = generator.get_policy_for_route(path, include_nonce=True)

        assert policy.nonce is not None
        assert len(policy.nonce) > 0

    @given(path=path_strategy())
    @settings(max_examples=100)
    def test_generator_nonces_unique(self, path: str) -> None:
        """**Property 12: Generator produces unique nonces**

        *For any* path, each call should produce a unique nonce.

        **Validates: Requirements 5.3**
        """
        generator = CSPGenerator()

        nonces = set()
        for _ in range(10):
            policy = generator.get_policy_for_route(path, include_nonce=True)
            nonces.add(policy.nonce)

        assert len(nonces) == 10

    @given(path=path_strategy())
    @settings(max_examples=100)
    def test_get_headers_returns_dict(self, path: str) -> None:
        """**Property 13: Get headers returns dictionary**

        *For any* path, get_headers should return a dictionary with
        the CSP header.

        **Validates: Requirements 5.3**
        """
        generator = CSPGenerator()
        headers = generator.get_headers(path)

        assert isinstance(headers, dict)
        assert len(headers) == 1
        assert "Content-Security-Policy" in headers or "Content-Security-Policy-Report-Only" in headers


# =============================================================================
# Property Tests - Route Matching
# =============================================================================

class TestRouteMatchingProperties:
    """Property tests for route matching."""

    @given(path=path_strategy())
    @settings(max_examples=100)
    def test_wildcard_matches_all(self, path: str) -> None:
        """**Property 14: Wildcard pattern matches all paths**

        *For any* path, the "*" pattern should match.

        **Validates: Requirements 5.3**
        """
        generator = CSPGenerator()
        custom_policy = CSPPolicy()
        custom_policy.add_source(CSPDirective.SCRIPT_SRC, "https://custom.com")

        generator.add_route_config(RouteCSPConfig(
            pattern="*",
            policy=custom_policy,
        ))

        policy = generator.get_policy_for_route(path)
        assert "https://custom.com" in policy.directives.get(CSPDirective.SCRIPT_SRC, [])

    def test_prefix_wildcard_matches(self) -> None:
        """**Property 15: Prefix wildcard matches paths with prefix**

        Paths starting with prefix should match /prefix/* pattern.

        **Validates: Requirements 5.3**
        """
        generator = CSPGenerator()
        custom_policy = CSPPolicy()
        custom_policy.add_source(CSPDirective.SCRIPT_SRC, "https://api.com")

        generator.add_route_config(RouteCSPConfig(
            pattern="/api/*",
            policy=custom_policy,
        ))

        # Should match
        policy1 = generator.get_policy_for_route("/api/users")
        assert "https://api.com" in policy1.directives.get(CSPDirective.SCRIPT_SRC, [])

        # Should not match
        policy2 = generator.get_policy_for_route("/web/users")
        assert "https://api.com" not in policy2.directives.get(CSPDirective.SCRIPT_SRC, [])

    def test_exact_match(self) -> None:
        """**Property 16: Exact pattern matches only exact path**

        Exact patterns should only match the exact path.

        **Validates: Requirements 5.3**
        """
        generator = CSPGenerator()
        custom_policy = CSPPolicy()
        custom_policy.add_source(CSPDirective.SCRIPT_SRC, "https://exact.com")

        generator.add_route_config(RouteCSPConfig(
            pattern="/exact/path",
            policy=custom_policy,
        ))

        # Should match
        policy1 = generator.get_policy_for_route("/exact/path")
        assert "https://exact.com" in policy1.directives.get(CSPDirective.SCRIPT_SRC, [])

        # Should not match
        policy2 = generator.get_policy_for_route("/exact/path/more")
        assert "https://exact.com" not in policy2.directives.get(CSPDirective.SCRIPT_SRC, [])


# =============================================================================
# Property Tests - Route Override
# =============================================================================

class TestRouteOverrideProperties:
    """Property tests for route override behavior."""

    def test_override_replaces_base_policy(self) -> None:
        """**Property 17: Override replaces base policy**

        When override=True, route policy should replace base policy.

        **Validates: Requirements 5.3**
        """
        base_policy = CSPPolicy()
        base_policy.add_source(CSPDirective.SCRIPT_SRC, "https://base.com")

        generator = CSPGenerator(base_policy=base_policy)

        override_policy = CSPPolicy()
        override_policy.add_source(CSPDirective.SCRIPT_SRC, "https://override.com")

        generator.add_route_config(RouteCSPConfig(
            pattern="/override/*",
            policy=override_policy,
            override=True,
        ))

        policy = generator.get_policy_for_route("/override/path")

        assert "https://override.com" in policy.directives.get(CSPDirective.SCRIPT_SRC, [])
        assert "https://base.com" not in policy.directives.get(CSPDirective.SCRIPT_SRC, [])

    def test_merge_combines_with_base(self) -> None:
        """**Property 18: Merge combines with base policy**

        When override=False, route policy should merge with base.

        **Validates: Requirements 5.3**
        """
        base_policy = CSPPolicy()
        base_policy.add_source(CSPDirective.SCRIPT_SRC, "https://base.com")

        generator = CSPGenerator(base_policy=base_policy)

        merge_policy = CSPPolicy()
        merge_policy.add_source(CSPDirective.SCRIPT_SRC, "https://merge.com")

        generator.add_route_config(RouteCSPConfig(
            pattern="/merge/*",
            policy=merge_policy,
            override=False,
        ))

        policy = generator.get_policy_for_route("/merge/path")

        assert "https://base.com" in policy.directives.get(CSPDirective.SCRIPT_SRC, [])
        assert "https://merge.com" in policy.directives.get(CSPDirective.SCRIPT_SRC, [])


# =============================================================================
# Property Tests - CSP Builder
# =============================================================================

class TestCSPBuilderProperties:
    """Property tests for CSP builder."""

    @given(source=csp_source_strategy())
    @settings(max_examples=100)
    def test_builder_fluent_api(self, source: str) -> None:
        """**Property 19: Builder supports fluent API**

        *For any* source, builder methods should return self for chaining.

        **Validates: Requirements 5.3**
        """
        builder = CSPBuilder()
        result = builder.default_src(source)

        assert result is builder

    def test_builder_produces_valid_policy(self) -> None:
        """**Property 20: Builder produces valid policy**

        Builder should produce a valid CSP policy with all set directives.

        **Validates: Requirements 5.3**
        """
        policy = (
            CSPBuilder()
            .default_src(CSPKeyword.SELF.value)
            .script_src(CSPKeyword.SELF.value, "https://cdn.com")
            .style_src(CSPKeyword.SELF.value)
            .build()
        )

        assert CSPDirective.DEFAULT_SRC in policy.directives
        assert CSPDirective.SCRIPT_SRC in policy.directives
        assert CSPDirective.STYLE_SRC in policy.directives
        assert "https://cdn.com" in policy.directives[CSPDirective.SCRIPT_SRC]


# =============================================================================
# Property Tests - Preset Policies
# =============================================================================

class TestPresetPoliciesProperties:
    """Property tests for preset policies."""

    def test_strict_policy_is_restrictive(self) -> None:
        """**Property 21: Strict policy is restrictive**

        Strict policy should have restrictive defaults.

        **Validates: Requirements 5.3**
        """
        policy = create_strict_policy()

        assert CSPKeyword.NONE.value in policy.directives.get(CSPDirective.DEFAULT_SRC, [])
        assert CSPKeyword.NONE.value in policy.directives.get(CSPDirective.FRAME_ANCESTORS, [])
        assert CSPKeyword.NONE.value in policy.directives.get(CSPDirective.OBJECT_SRC, [])

    def test_relaxed_policy_allows_inline(self) -> None:
        """**Property 22: Relaxed policy allows inline**

        Relaxed policy should allow unsafe-inline for development.

        **Validates: Requirements 5.3**
        """
        policy = create_relaxed_policy()

        assert CSPKeyword.UNSAFE_INLINE.value in policy.directives.get(CSPDirective.SCRIPT_SRC, [])
        assert CSPKeyword.UNSAFE_INLINE.value in policy.directives.get(CSPDirective.STYLE_SRC, [])
