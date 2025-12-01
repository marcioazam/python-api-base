"""Property-based tests for Developer Portal.

**Feature: api-architecture-analysis, Property: Developer portal operations**
**Validates: Requirements 18.6**
"""

import pytest
from hypothesis import given, strategies as st, settings

from my_app.interface.api.developer_portal import (
    DeveloperPortal,
    SubscriptionTier,
    TIER_LIMITS,
    InMemoryDeveloperStore,
    InMemoryAPIKeyStore,
)


class InMemoryUsageStore:
    """In-memory usage store for testing."""

    async def record(self, developer_id: str, endpoint: str, success: bool, latency_ms: float) -> None:
        pass

    async def get_stats(self, developer_id: str, start, end):
        from my_app.interface.api.developer_portal import UsageStats
        return UsageStats(
            developer_id=developer_id,
            period_start=start,
            period_end=end
        )


class TestDeveloperPortalProperties:
    """Property tests for developer portal."""

    @given(
        st.emails(),
        st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_register_creates_developer(
        self,
        email: str,
        name: str
    ) -> None:
        """Registration creates developer with correct data."""
        portal = DeveloperPortal(
            InMemoryDeveloperStore(),
            InMemoryAPIKeyStore(),
            InMemoryUsageStore()
        )

        developer = await portal.register_developer(email, name)

        assert developer.email == email
        assert developer.name == name
        assert developer.tier == SubscriptionTier.FREE

    @given(st.emails())
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_duplicate_email_rejected(self, email: str) -> None:
        """Duplicate email registration is rejected."""
        portal = DeveloperPortal(
            InMemoryDeveloperStore(),
            InMemoryAPIKeyStore(),
            InMemoryUsageStore()
        )

        await portal.register_developer(email, "Test User")

        with pytest.raises(ValueError, match="already registered"):
            await portal.register_developer(email, "Another User")

    @given(
        st.emails(),
        st.text(min_size=1, max_size=20)
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_api_key_creation(self, email: str, key_name: str) -> None:
        """API key creation returns valid key."""
        portal = DeveloperPortal(
            InMemoryDeveloperStore(),
            InMemoryAPIKeyStore(),
            InMemoryUsageStore()
        )

        developer = await portal.register_developer(email, "Test")
        raw_key, key_info = await portal.create_api_key(developer.id, key_name)

        assert raw_key.startswith("sk_")
        assert key_info.developer_id == developer.id
        assert key_info.name == key_name

    @given(st.emails())
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_api_key_validation(self, email: str) -> None:
        """Created API key can be validated."""
        portal = DeveloperPortal(
            InMemoryDeveloperStore(),
            InMemoryAPIKeyStore(),
            InMemoryUsageStore()
        )

        developer = await portal.register_developer(email, "Test")
        raw_key, _ = await portal.create_api_key(developer.id, "test-key")

        validated = await portal.validate_api_key(raw_key)
        assert validated is not None
        assert validated.developer_id == developer.id

    @given(st.emails())
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_invalid_key_rejected(self, email: str) -> None:
        """Invalid API key is rejected."""
        portal = DeveloperPortal(
            InMemoryDeveloperStore(),
            InMemoryAPIKeyStore(),
            InMemoryUsageStore()
        )

        validated = await portal.validate_api_key("sk_invalid_key")
        assert validated is None

    @given(st.emails())
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_revoked_key_invalid(self, email: str) -> None:
        """Revoked API key becomes invalid."""
        portal = DeveloperPortal(
            InMemoryDeveloperStore(),
            InMemoryAPIKeyStore(),
            InMemoryUsageStore()
        )

        developer = await portal.register_developer(email, "Test")
        raw_key, key_info = await portal.create_api_key(developer.id, "test-key")

        await portal.revoke_api_key(developer.id, key_info.key_id)

        validated = await portal.validate_api_key(raw_key)
        assert validated is None

    @given(
        st.emails(),
        st.sampled_from(list(SubscriptionTier))
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_tier_upgrade(self, email: str, new_tier: SubscriptionTier) -> None:
        """Tier upgrade updates developer."""
        portal = DeveloperPortal(
            InMemoryDeveloperStore(),
            InMemoryAPIKeyStore(),
            InMemoryUsageStore()
        )

        developer = await portal.register_developer(email, "Test")
        upgraded = await portal.upgrade_tier(developer.id, new_tier)

        assert upgraded.tier == new_tier


class TestTierLimitsProperties:
    """Property tests for tier limits."""

    @given(st.sampled_from(list(SubscriptionTier)))
    @settings(max_examples=10)
    def test_all_tiers_have_limits(self, tier: SubscriptionTier) -> None:
        """All tiers have defined limits."""
        limits = TIER_LIMITS[tier]
        assert limits.requests_per_minute > 0
        assert limits.requests_per_day > 0
        assert limits.max_api_keys > 0

    def test_higher_tiers_have_higher_limits(self) -> None:
        """Higher tiers have higher limits."""
        tiers = [
            SubscriptionTier.FREE,
            SubscriptionTier.STARTER,
            SubscriptionTier.PROFESSIONAL,
            SubscriptionTier.ENTERPRISE
        ]

        for i in range(len(tiers) - 1):
            lower = TIER_LIMITS[tiers[i]]
            higher = TIER_LIMITS[tiers[i + 1]]
            assert higher.requests_per_minute >= lower.requests_per_minute
            assert higher.requests_per_day >= lower.requests_per_day
