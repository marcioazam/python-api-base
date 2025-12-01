"""Property tests for csp_generator module.

**Feature: shared-modules-phase2**
**Validates: Requirements 3.1, 3.2, 4.3**
"""

import base64

import pytest
from hypothesis import given, settings, strategies as st

from my_app.interface.api.csp_generator import (
    CSPBuilder,
    CSPDirective,
    CSPGenerator,
    CSPKeyword,
    CSPPolicy,
)


class TestNonceEntropy:
    """Property tests for nonce entropy.

    **Feature: shared-modules-phase2, Property 6: Nonce Entropy**
    **Validates: Requirements 3.1**
    """

    @settings(max_examples=100)
    @given(nonce_length=st.integers(min_value=16, max_value=64))
    def test_nonce_has_minimum_entropy(self, nonce_length: int) -> None:
        """Generated nonce should have at least 16 bytes of entropy."""
        generator = CSPGenerator(nonce_length=nonce_length)
        nonce = generator.generate_nonce()

        # URL-safe base64 encoding: 4 chars = 3 bytes
        # So 16 bytes = ceil(16 * 4 / 3) = 22 chars minimum
        # But token_urlsafe returns slightly more due to padding
        decoded = base64.urlsafe_b64decode(nonce + "==")  # Add padding
        assert len(decoded) >= nonce_length

    def test_nonce_uses_secrets_module(self) -> None:
        """Nonce generation should use cryptographically secure random."""
        generator = CSPGenerator(nonce_length=16)
        nonces = [generator.generate_nonce() for _ in range(100)]

        # All nonces should be unique (extremely high probability)
        assert len(set(nonces)) == 100


class TestNonceUniqueness:
    """Property tests for nonce uniqueness.

    **Feature: shared-modules-phase2, Property 5: Nonce Uniqueness**
    **Validates: Requirements 3.2**
    """

    @settings(max_examples=100)
    @given(route=st.text(min_size=1, max_size=100))
    def test_same_route_different_nonces(self, route: str) -> None:
        """Same route should generate different nonces each time."""
        generator = CSPGenerator()

        nonces = []
        for _ in range(10):
            policy = generator.get_policy_for_route(route, include_nonce=True)
            if policy.nonce:
                nonces.append(policy.nonce)

        # All nonces should be unique
        assert len(set(nonces)) == len(nonces)

    def test_multiple_routes_unique_nonces(self) -> None:
        """Different routes should also have unique nonces."""
        generator = CSPGenerator()
        routes = ["/api/v1", "/api/v2", "/users", "/admin", "/health"]

        nonces = []
        for route in routes:
            policy = generator.get_policy_for_route(route, include_nonce=True)
            if policy.nonce:
                nonces.append(policy.nonce)

        assert len(set(nonces)) == len(nonces)


class TestCSPHeaderDeterminism:
    """Property tests for CSP header determinism.

    **Feature: shared-modules-phase2, Property 7: CSP Header Determinism**
    **Validates: Requirements 4.3**
    """

    @settings(max_examples=100)
    @given(
        sources=st.lists(
            st.sampled_from(["'self'", "'none'", "https:", "data:", "blob:"]),
            min_size=1,
            max_size=5,
        )
    )
    def test_same_policy_same_header(self, sources: list[str]) -> None:
        """Same policy should produce identical headers."""
        policy = CSPPolicy()
        for source in sources:
            policy.add_source(CSPDirective.DEFAULT_SRC, source)

        # Generate header multiple times
        headers = [policy.to_header_value() for _ in range(10)]

        # All headers should be identical
        assert len(set(headers)) == 1

    def test_builder_produces_deterministic_headers(self) -> None:
        """Builder should produce deterministic headers."""
        headers = []
        for _ in range(10):
            policy = (
                CSPBuilder()
                .default_src(CSPKeyword.SELF.value)
                .script_src(CSPKeyword.SELF.value, "https://cdn.example.com")
                .style_src(CSPKeyword.SELF.value, CSPKeyword.UNSAFE_INLINE.value)
                .build()
            )
            headers.append(policy.to_header_value())

        assert len(set(headers)) == 1


class TestNonceFormat:
    """Test nonce format in CSP headers."""

    def test_nonce_format_in_header(self) -> None:
        """Nonce should be properly formatted in header."""
        generator = CSPGenerator()
        policy = generator.get_policy_for_route("/test", include_nonce=True)

        header = policy.to_header_value()

        # Nonce should be in format 'nonce-{base64}'
        assert f"'nonce-{policy.nonce}'" in header

    def test_nonce_only_in_script_and_style(self) -> None:
        """Nonce should only appear in script-src and style-src."""
        policy = CSPPolicy(
            directives={
                CSPDirective.DEFAULT_SRC: [CSPKeyword.SELF.value],
                CSPDirective.SCRIPT_SRC: [CSPKeyword.SELF.value],
                CSPDirective.STYLE_SRC: [CSPKeyword.SELF.value],
                CSPDirective.IMG_SRC: [CSPKeyword.SELF.value],
            },
            nonce="test-nonce-123",
        )

        header = policy.to_header_value()

        # Nonce should be in script-src and style-src
        assert "script-src 'self' 'nonce-test-nonce-123'" in header
        assert "style-src 'self' 'nonce-test-nonce-123'" in header

        # Nonce should NOT be in default-src or img-src
        assert "default-src 'self' 'nonce" not in header
        assert "img-src 'self' 'nonce" not in header
