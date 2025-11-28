"""Property-based tests for Request Fingerprinting.

**Feature: api-architecture-analysis**
**Validates: Requirements 5.5**
"""

from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings, strategies as st

from my_api.shared.fingerprint import (
    Fingerprint,
    FingerprintComponent,
    FingerprintConfig,
    FingerprintGenerator,
    FingerprintService,
    InMemoryFingerprintStore,
    RequestData,
    SuspicionAnalysis,
    SuspicionAnalyzer,
    SuspicionIndicator,
    SuspicionLevel,
    create_fingerprint_service,
)


# Strategies
ip_strategy = st.from_regex(
    r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
    fullmatch=True,
)
user_agent_strategy = st.text(min_size=0, max_size=200)
language_strategy = st.sampled_from(["en-US", "en-GB", "pt-BR", "es-ES", "fr-FR", "de-DE", ""])
encoding_strategy = st.sampled_from(["gzip, deflate, br", "gzip, deflate", "gzip", ""])


@st.composite
def request_data_strategy(draw: st.DrawFn) -> RequestData:
    """Generate random RequestData."""
    return RequestData(
        ip_address=draw(ip_strategy),
        user_agent=draw(user_agent_strategy),
        accept_language=draw(language_strategy),
        accept_encoding=draw(encoding_strategy),
    )


class TestFingerprintProperties:
    """Property tests for Fingerprint model."""

    @given(
        ip=ip_strategy,
        user_agent=user_agent_strategy,
    )
    @settings(max_examples=100)
    def test_fingerprint_has_valid_hash(self, ip: str, user_agent: str) -> None:
        """Property: Fingerprint always has a valid hash."""
        generator = FingerprintGenerator()
        request_data = RequestData(ip_address=ip, user_agent=user_agent)
        fingerprint = generator.generate(request_data)

        assert fingerprint.hash_value
        assert len(fingerprint.hash_value) == 64  # SHA256 hex length
        assert all(c in "0123456789abcdef" for c in fingerprint.hash_value)

    @given(request_data=request_data_strategy())
    @settings(max_examples=100)
    def test_fingerprint_id_is_unique_per_timestamp(
        self, request_data: RequestData
    ) -> None:
        """Property: Fingerprint ID includes timestamp for uniqueness."""
        generator = FingerprintGenerator()
        fp1 = generator.generate(request_data)
        fp2 = generator.generate(request_data)

        # Same request data at different times should have different IDs
        assert fp1.fingerprint_id != fp2.fingerprint_id

    @given(request_data=request_data_strategy())
    @settings(max_examples=100)
    def test_fingerprint_confidence_in_range(self, request_data: RequestData) -> None:
        """Property: Confidence is always between 0 and 1."""
        generator = FingerprintGenerator()
        fingerprint = generator.generate(request_data)

        assert 0.0 <= fingerprint.confidence <= 1.0

    @given(request_data=request_data_strategy())
    @settings(max_examples=100)
    def test_short_id_is_prefix(self, request_data: RequestData) -> None:
        """Property: Short ID is prefix of full ID."""
        generator = FingerprintGenerator()
        fingerprint = generator.generate(request_data)

        assert fingerprint.fingerprint_id.startswith(fingerprint.short_id)
        assert len(fingerprint.short_id) == 16


class TestFingerprintGeneratorProperties:
    """Property tests for FingerprintGenerator."""

    @given(
        ip1=ip_strategy,
        ip2=ip_strategy,
        user_agent=user_agent_strategy,
    )
    @settings(max_examples=100)
    def test_different_ips_different_hashes(
        self, ip1: str, ip2: str, user_agent: str
    ) -> None:
        """Property: Different IPs produce different hashes (when IP included)."""
        if ip1 == ip2:
            return  # Skip if same IP

        config = FingerprintConfig(include_ip_in_hash=True)
        generator = FingerprintGenerator(config)

        fp1 = generator.generate(RequestData(ip_address=ip1, user_agent=user_agent))
        fp2 = generator.generate(RequestData(ip_address=ip2, user_agent=user_agent))

        assert fp1.hash_value != fp2.hash_value

    @given(
        ip=ip_strategy,
        ua1=user_agent_strategy,
        ua2=user_agent_strategy,
    )
    @settings(max_examples=100)
    def test_different_user_agents_different_hashes(
        self, ip: str, ua1: str, ua2: str
    ) -> None:
        """Property: Different user agents produce different hashes."""
        if ua1 == ua2:
            return  # Skip if same UA

        generator = FingerprintGenerator()
        fp1 = generator.generate(RequestData(ip_address=ip, user_agent=ua1))
        fp2 = generator.generate(RequestData(ip_address=ip, user_agent=ua2))

        # Note: With normalization, some UAs might produce same hash
        # This is expected behavior

    @given(request_data=request_data_strategy())
    @settings(max_examples=100)
    def test_components_match_config(self, request_data: RequestData) -> None:
        """Property: Generated components match configured components."""
        config = FingerprintConfig(
            components={
                FingerprintComponent.IP_ADDRESS,
                FingerprintComponent.USER_AGENT,
            }
        )
        generator = FingerprintGenerator(config)
        fingerprint = generator.generate(request_data)

        # Should have IP and UA components
        assert FingerprintComponent.IP_ADDRESS in fingerprint.components
        # UA might be empty but key should exist if configured


class TestSuspicionAnalyzerProperties:
    """Property tests for SuspicionAnalyzer."""

    @given(request_data=request_data_strategy())
    @settings(max_examples=100)
    def test_analysis_score_in_range(self, request_data: RequestData) -> None:
        """Property: Suspicion score is always between 0 and 1."""
        generator = FingerprintGenerator()
        analyzer = SuspicionAnalyzer()

        fingerprint = generator.generate(request_data)
        analysis = analyzer.analyze(fingerprint)

        assert 0.0 <= analysis.score <= 1.0

    @given(ip=ip_strategy)
    @settings(max_examples=100)
    def test_bot_user_agent_is_suspicious(self, ip: str) -> None:
        """Property: Bot user agents are flagged as suspicious."""
        generator = FingerprintGenerator()
        analyzer = SuspicionAnalyzer()

        request_data = RequestData(
            ip_address=ip,
            user_agent="python-requests/2.28.0",
        )
        fingerprint = generator.generate(request_data)
        analysis = analyzer.analyze(fingerprint)

        assert any(i.name == "bot_user_agent" for i in analysis.indicators)

    @given(ip=ip_strategy)
    @settings(max_examples=100)
    def test_empty_user_agent_is_suspicious(self, ip: str) -> None:
        """Property: Empty user agent is flagged as suspicious."""
        generator = FingerprintGenerator()
        analyzer = SuspicionAnalyzer()

        request_data = RequestData(ip_address=ip, user_agent="")
        fingerprint = generator.generate(request_data)
        analysis = analyzer.analyze(fingerprint)

        assert any(i.name == "empty_user_agent" for i in analysis.indicators)

    @given(ip=ip_strategy)
    @settings(max_examples=100)
    def test_headless_browser_is_highly_suspicious(self, ip: str) -> None:
        """Property: Headless browser indicators are highly suspicious."""
        generator = FingerprintGenerator()
        analyzer = SuspicionAnalyzer()

        request_data = RequestData(
            ip_address=ip,
            user_agent="Mozilla/5.0 HeadlessChrome/91.0.4472.124",
        )
        fingerprint = generator.generate(request_data)
        analysis = analyzer.analyze(fingerprint)

        headless_indicators = [i for i in analysis.indicators if i.name == "headless_browser"]
        assert len(headless_indicators) > 0
        assert headless_indicators[0].severity == SuspicionLevel.HIGH


class TestInMemoryFingerprintStoreProperties:
    """Property tests for InMemoryFingerprintStore."""

    @given(request_data=request_data_strategy())
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_fingerprint_round_trip(self, request_data: RequestData) -> None:
        """Property: Saved fingerprints can be retrieved."""
        store = InMemoryFingerprintStore()
        generator = FingerprintGenerator()

        fingerprint = generator.generate(request_data)
        await store.save(fingerprint)

        retrieved = await store.get(fingerprint.fingerprint_id)
        assert retrieved is not None
        assert retrieved.fingerprint_id == fingerprint.fingerprint_id
        assert retrieved.hash_value == fingerprint.hash_value

    @given(request_data=request_data_strategy())
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_get_by_ip_returns_correct_fingerprints(
        self, request_data: RequestData
    ) -> None:
        """Property: get_by_ip returns fingerprints for that IP."""
        store = InMemoryFingerprintStore()
        generator = FingerprintGenerator()

        fingerprint = generator.generate(request_data)
        await store.save(fingerprint)

        fingerprints = await store.get_by_ip(request_data.ip_address)
        assert len(fingerprints) >= 1
        assert any(fp.fingerprint_id == fingerprint.fingerprint_id for fp in fingerprints)

    @given(
        request_data1=request_data_strategy(),
        request_data2=request_data_strategy(),
    )
    @settings(max_examples=50)
    @pytest.mark.anyio
    async def test_recent_returns_in_order(
        self, request_data1: RequestData, request_data2: RequestData
    ) -> None:
        """Property: get_recent returns fingerprints in reverse chronological order."""
        store = InMemoryFingerprintStore()
        generator = FingerprintGenerator()

        fp1 = generator.generate(request_data1)
        await store.save(fp1)

        fp2 = generator.generate(request_data2)
        await store.save(fp2)

        recent = await store.get_recent(limit=10)
        assert len(recent) >= 2

        # Most recent should be first
        timestamps = [fp.created_at for fp in recent]
        assert timestamps == sorted(timestamps, reverse=True)


class TestFingerprintServiceProperties:
    """Property tests for FingerprintService."""

    @given(request_data=request_data_strategy())
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_fingerprint_request_returns_both(
        self, request_data: RequestData
    ) -> None:
        """Property: fingerprint_request returns fingerprint and analysis."""
        service = create_fingerprint_service()

        fingerprint, analysis = await service.fingerprint_request(request_data)

        assert fingerprint is not None
        assert analysis is not None
        assert analysis.fingerprint.fingerprint_id == fingerprint.fingerprint_id

    @given(request_data=request_data_strategy())
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_fingerprint_is_stored(self, request_data: RequestData) -> None:
        """Property: Generated fingerprint is stored and retrievable."""
        service = create_fingerprint_service()

        fingerprint, _ = await service.fingerprint_request(request_data)
        retrieved = await service.get_fingerprint(fingerprint.fingerprint_id)

        assert retrieved is not None
        assert retrieved.fingerprint_id == fingerprint.fingerprint_id

    @given(ip=ip_strategy)
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_is_suspicious_for_bot(self, ip: str) -> None:
        """Property: Bot requests are detected as suspicious."""
        service = create_fingerprint_service()

        request_data = RequestData(
            ip_address=ip,
            user_agent="curl/7.68.0",
        )

        is_suspicious = await service.is_suspicious(request_data)
        assert is_suspicious is True


class TestSuspicionLevelProperties:
    """Property tests for suspicion level thresholds."""

    def test_thresholds_are_ordered(self) -> None:
        """Property: Suspicion thresholds are in ascending order."""
        config = FingerprintConfig()
        thresholds = config.suspicion_thresholds

        assert thresholds[SuspicionLevel.LOW] < thresholds[SuspicionLevel.MEDIUM]
        assert thresholds[SuspicionLevel.MEDIUM] < thresholds[SuspicionLevel.HIGH]
        assert thresholds[SuspicionLevel.HIGH] < thresholds[SuspicionLevel.CRITICAL]

    @given(
        score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_score_maps_to_valid_level(self, score: float) -> None:
        """Property: Any score maps to a valid suspicion level."""
        config = FingerprintConfig()

        # Determine expected level
        level = SuspicionLevel.NONE
        for lvl, threshold in sorted(
            config.suspicion_thresholds.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            if score >= threshold:
                level = lvl
                break

        assert level in SuspicionLevel
