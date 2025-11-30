"""Property tests for fingerprint module.

**Feature: shared-modules-phase2**
**Validates: Requirements 9.1, 9.2, 10.1, 10.3**
"""

import pytest
from hypothesis import given, settings, strategies as st

from my_api.shared.fingerprint import (
    Fingerprint,
    FingerprintComponent,
    FingerprintConfig,
    FingerprintGenerator,
    RequestData,
    SuspicionAnalyzer,
    SuspicionLevel,
)


class TestFingerprintComponentExclusion:
    """Property tests for fingerprint component exclusion.

    **Feature: shared-modules-phase2, Property 15: Fingerprint Component Exclusion**
    **Validates: Requirements 9.1**
    """

    @settings(max_examples=100)
    @given(
        ip=st.ip_addresses(v=4).map(str),
        user_agent=st.text(min_size=1, max_size=100),
    )
    def test_excluded_components_not_in_fingerprint(
        self, ip: str, user_agent: str
    ) -> None:
        """Excluded components should not appear in fingerprint."""
        config = FingerprintConfig(
            components={
                FingerprintComponent.USER_AGENT,
                FingerprintComponent.ACCEPT_LANGUAGE,
            }
        )
        generator = FingerprintGenerator(config)

        request_data = RequestData(
            ip_address=ip,
            user_agent=user_agent,
            accept_language="en-US",
        )

        fingerprint = generator.generate(request_data)

        # IP should not be in components (excluded)
        assert FingerprintComponent.IP_ADDRESS not in fingerprint.components


class TestFingerprintValidityWithoutIP:
    """Property tests for fingerprint validity without IP.

    **Feature: shared-modules-phase2, Property 16: Fingerprint Validity Without IP**
    **Validates: Requirements 9.2**
    """

    @settings(max_examples=100)
    @given(
        user_agent=st.text(min_size=1, max_size=100),
        accept_language=st.text(min_size=1, max_size=50),
    )
    def test_fingerprint_valid_without_ip(
        self, user_agent: str, accept_language: str
    ) -> None:
        """Fingerprint should be valid even without IP component."""
        config = FingerprintConfig(
            components={
                FingerprintComponent.USER_AGENT,
                FingerprintComponent.ACCEPT_LANGUAGE,
            },
            include_ip_in_hash=False,
        )
        generator = FingerprintGenerator(config)

        request_data = RequestData(
            ip_address="192.168.1.1",
            user_agent=user_agent,
            accept_language=accept_language,
        )

        fingerprint = generator.generate(request_data)

        # Fingerprint should be valid
        assert fingerprint.fingerprint_id
        assert fingerprint.hash_value
        assert len(fingerprint.hash_value) > 0


class TestFingerprintHashAlgorithm:
    """Property tests for fingerprint hash algorithm.

    **Feature: shared-modules-phase2, Property 17: Fingerprint Hash Algorithm**
    **Validates: Requirements 10.1**
    """

    def test_default_hash_algorithm_is_sha256(self) -> None:
        """Default hash algorithm should be SHA-256."""
        config = FingerprintConfig()
        assert config.hash_algorithm == "sha256"

    @settings(max_examples=100)
    @given(
        ip=st.ip_addresses(v=4).map(str),
        user_agent=st.text(min_size=1, max_size=100),
    )
    def test_hash_is_64_chars_hex(self, ip: str, user_agent: str) -> None:
        """SHA-256 hash should be 64 hex characters."""
        generator = FingerprintGenerator()

        request_data = RequestData(
            ip_address=ip,
            user_agent=user_agent,
        )

        fingerprint = generator.generate(request_data)

        # SHA-256 produces 64 hex characters
        assert len(fingerprint.hash_value) == 64
        assert all(c in "0123456789abcdef" for c in fingerprint.hash_value)


class TestLowConfidenceIndication:
    """Property tests for low confidence indication.

    **Feature: shared-modules-phase2, Property 18: Low Confidence Indication**
    **Validates: Requirements 10.3**
    """

    def test_low_confidence_with_few_components(self) -> None:
        """Fingerprint with few components should have low confidence."""
        config = FingerprintConfig(
            components={
                FingerprintComponent.IP_ADDRESS,
                FingerprintComponent.USER_AGENT,
                FingerprintComponent.ACCEPT_LANGUAGE,
                FingerprintComponent.ACCEPT_ENCODING,
            }
        )
        generator = FingerprintGenerator(config)

        # Request with only IP (missing other components)
        request_data = RequestData(
            ip_address="192.168.1.1",
            user_agent="",  # Empty
            accept_language="",  # Empty
            accept_encoding="",  # Empty
        )

        fingerprint = generator.generate(request_data)

        # Confidence should be low (only 1 of 4 components)
        assert fingerprint.confidence < 0.5

    def test_high_confidence_with_all_components(self) -> None:
        """Fingerprint with all components should have high confidence."""
        config = FingerprintConfig(
            components={
                FingerprintComponent.IP_ADDRESS,
                FingerprintComponent.USER_AGENT,
                FingerprintComponent.ACCEPT_LANGUAGE,
                FingerprintComponent.ACCEPT_ENCODING,
            }
        )
        generator = FingerprintGenerator(config)

        request_data = RequestData(
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            accept_language="en-US",
            accept_encoding="gzip, deflate",
        )

        fingerprint = generator.generate(request_data)

        # Confidence should be high (all 4 components present)
        assert fingerprint.confidence == 1.0


class TestSuspicionAnalysis:
    """Test suspicion analysis functionality."""

    def test_bot_user_agent_detected(self) -> None:
        """Bot user agents should be detected as suspicious."""
        config = FingerprintConfig()
        generator = FingerprintGenerator(config)
        analyzer = SuspicionAnalyzer(config)

        request_data = RequestData(
            ip_address="192.168.1.1",
            user_agent="python-requests/2.28.0",
        )

        fingerprint = generator.generate(request_data)
        analysis = analyzer.analyze(fingerprint)

        assert analysis.is_suspicious or analysis.overall_level != SuspicionLevel.NONE

    def test_normal_browser_not_suspicious(self) -> None:
        """Normal browser user agents should not be suspicious."""
        config = FingerprintConfig()
        generator = FingerprintGenerator(config)
        analyzer = SuspicionAnalyzer(config)

        request_data = RequestData(
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            accept_language="en-US,en;q=0.9",
            accept_encoding="gzip, deflate, br",
        )

        fingerprint = generator.generate(request_data)
        analysis = analyzer.analyze(fingerprint)

        # Should have low or no suspicion
        assert analysis.overall_level in (SuspicionLevel.NONE, SuspicionLevel.LOW)
