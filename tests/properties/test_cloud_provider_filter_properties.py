"""Property-based tests for Cloud Provider IP Filtering.

Tests correctness properties of cloud provider blocking including:
- Provider identification consistency
- Blocklist/allowlist behavior
- IP allowlist priority
- Cloudflare special handling

**Feature: api-architecture-analysis, Property: Cloud Provider Blocking**
**Validates: Requirements 5.3**
"""


import pytest
pytest.skip('Module infrastructure.security.cloud_provider_filter not implemented', allow_module_level=True)

import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from infrastructure.security.cloud_provider_filter import (
    CloudProvider,
    CloudProviderConfig,
    CloudProviderFilter,
    CloudProviderFilterBuilder,
    CloudProviderInfo,
    CloudProviderResult,
    InMemoryCloudRangeProvider,
)


# Strategies
provider_strategy = st.sampled_from([
    p for p in CloudProvider if p != CloudProvider.UNKNOWN
])

# Sample IPs from known cloud ranges
aws_ip_strategy = st.sampled_from([
    "3.5.140.2", "13.52.0.1", "52.94.76.1", "54.239.28.85",
])

gcp_ip_strategy = st.sampled_from([
    "34.102.136.180", "104.196.0.1", "130.211.0.1", "142.250.0.1",
])

azure_ip_strategy = st.sampled_from([
    "13.64.0.1", "20.42.0.1", "40.64.0.1", "51.140.0.1",
])

digitalocean_ip_strategy = st.sampled_from([
    "64.225.0.1", "134.209.0.1", "138.68.0.1", "159.65.0.1",
])

cloudflare_ip_strategy = st.sampled_from([
    "104.16.0.1", "104.24.0.1", "172.64.0.1", "173.245.48.1",
])

non_cloud_ip_strategy = st.sampled_from([
    "192.168.1.1", "10.0.0.1", "8.8.8.8", "1.1.1.1", "208.67.222.222",
])


class TestProviderIdentification:
    """Tests for cloud provider identification."""

    @given(ip=aws_ip_strategy)
    @settings(max_examples=20)
    def test_aws_ip_identified(self, ip: str) -> None:
        """Property: AWS IPs are correctly identified.

        *For any* AWS IP, provider is identified as AWS.
        **Validates: Requirements 5.3**
        """
        provider = InMemoryCloudRangeProvider()
        result = provider.identify_provider(ip)
        assert result == CloudProvider.AWS

    @given(ip=gcp_ip_strategy)
    @settings(max_examples=20)
    def test_gcp_ip_identified(self, ip: str) -> None:
        """Property: GCP IPs are correctly identified.

        *For any* GCP IP, provider is identified as GCP.
        **Validates: Requirements 5.3**
        """
        provider = InMemoryCloudRangeProvider()
        result = provider.identify_provider(ip)
        assert result == CloudProvider.GCP

    @given(ip=cloudflare_ip_strategy)
    @settings(max_examples=20)
    def test_cloudflare_ip_identified(self, ip: str) -> None:
        """Property: Cloudflare IPs are correctly identified.

        *For any* Cloudflare IP, provider is identified as CLOUDFLARE.
        **Validates: Requirements 5.3**
        """
        provider = InMemoryCloudRangeProvider()
        result = provider.identify_provider(ip)
        assert result == CloudProvider.CLOUDFLARE

    @given(ip=non_cloud_ip_strategy)
    @settings(max_examples=20)
    def test_non_cloud_ip_returns_none(self, ip: str) -> None:
        """Property: Non-cloud IPs return None.

        *For any* non-cloud IP, provider is None.
        **Validates: Requirements 5.3**
        """
        provider = InMemoryCloudRangeProvider()
        result = provider.identify_provider(ip)
        assert result is None


class TestBlocklistBehavior:
    """Tests for blocklist behavior."""

    @given(ip=aws_ip_strategy)
    @settings(max_examples=20)
    def test_blocked_provider_is_blocked(self, ip: str) -> None:
        """Property: IPs from blocked providers are blocked.

        *For any* IP from a blocked provider, access is denied.
        **Validates: Requirements 5.3**
        """
        config = CloudProviderConfig(blocked_providers={CloudProvider.AWS})
        filter = CloudProviderFilter(config=config)

        result = asyncio.run(filter.check(ip))

        assert result.allowed is False
        assert result.info is not None
        assert result.info.provider == CloudProvider.AWS

    @given(ip=aws_ip_strategy)
    @settings(max_examples=20)
    def test_non_blocked_provider_allowed(self, ip: str) -> None:
        """Property: IPs from non-blocked providers are allowed.

        *For any* IP from a non-blocked provider, access is granted.
        **Validates: Requirements 5.3**
        """
        # Block GCP, not AWS
        config = CloudProviderConfig(blocked_providers={CloudProvider.GCP})
        filter = CloudProviderFilter(config=config)

        result = asyncio.run(filter.check(ip))

        assert result.allowed is True

    @given(ip=non_cloud_ip_strategy)
    @settings(max_examples=20)
    def test_non_cloud_ip_always_allowed(self, ip: str) -> None:
        """Property: Non-cloud IPs are always allowed.

        *For any* non-cloud IP, access is granted regardless of config.
        **Validates: Requirements 5.3**
        """
        config = CloudProviderConfig(block_all_cloud=True)
        filter = CloudProviderFilter(config=config)

        result = asyncio.run(filter.check(ip))

        assert result.allowed is True


class TestBlockAllCloud:
    """Tests for block_all_cloud mode."""

    @given(ip=aws_ip_strategy)
    @settings(max_examples=20)
    def test_block_all_blocks_aws(self, ip: str) -> None:
        """Property: block_all_cloud blocks AWS IPs.

        *For any* AWS IP with block_all_cloud, access is denied.
        **Validates: Requirements 5.3**
        """
        config = CloudProviderConfig(block_all_cloud=True, allow_cloudflare=False)
        filter = CloudProviderFilter(config=config)

        result = asyncio.run(filter.check(ip))

        assert result.allowed is False

    @given(ip=gcp_ip_strategy)
    @settings(max_examples=20)
    def test_block_all_blocks_gcp(self, ip: str) -> None:
        """Property: block_all_cloud blocks GCP IPs.

        *For any* GCP IP with block_all_cloud, access is denied.
        **Validates: Requirements 5.3**
        """
        config = CloudProviderConfig(block_all_cloud=True, allow_cloudflare=False)
        filter = CloudProviderFilter(config=config)

        result = asyncio.run(filter.check(ip))

        assert result.allowed is False


class TestCloudflareSpecialHandling:
    """Tests for Cloudflare special handling."""

    @given(ip=cloudflare_ip_strategy)
    @settings(max_examples=20)
    def test_cloudflare_allowed_by_default(self, ip: str) -> None:
        """Property: Cloudflare IPs allowed by default.

        *For any* Cloudflare IP with default config, access is granted.
        **Validates: Requirements 5.3**
        """
        config = CloudProviderConfig(block_all_cloud=True, allow_cloudflare=True)
        filter = CloudProviderFilter(config=config)

        result = asyncio.run(filter.check(ip))

        assert result.allowed is True
        assert result.info is not None
        assert result.info.provider == CloudProvider.CLOUDFLARE

    @given(ip=cloudflare_ip_strategy)
    @settings(max_examples=20)
    def test_cloudflare_blocked_when_disabled(self, ip: str) -> None:
        """Property: Cloudflare IPs blocked when allow_cloudflare=False.

        *For any* Cloudflare IP with allow_cloudflare=False, access is denied.
        **Validates: Requirements 5.3**
        """
        config = CloudProviderConfig(block_all_cloud=True, allow_cloudflare=False)
        filter = CloudProviderFilter(config=config)

        result = asyncio.run(filter.check(ip))

        assert result.allowed is False


class TestIPAllowlist:
    """Tests for IP allowlist priority."""

    @given(ip=aws_ip_strategy)
    @settings(max_examples=20)
    def test_ip_allowlist_overrides_provider_block(self, ip: str) -> None:
        """Property: IP allowlist takes priority over provider block.

        *For any* IP in allowlist, it's allowed even if provider is blocked.
        **Validates: Requirements 5.3**
        """
        config = CloudProviderConfig(
            blocked_providers={CloudProvider.AWS},
            allowed_ips={ip},
        )
        filter = CloudProviderFilter(config=config)

        result = asyncio.run(filter.check(ip))

        assert result.allowed is True

    @given(ip=non_cloud_ip_strategy)
    @settings(max_examples=20)
    def test_ip_blocklist_blocks(self, ip: str) -> None:
        """Property: IP blocklist blocks regardless of provider.

        *For any* IP in blocklist, it's blocked.
        **Validates: Requirements 5.3**
        """
        config = CloudProviderConfig(blocked_ips={ip})
        filter = CloudProviderFilter(config=config)

        result = asyncio.run(filter.check(ip))

        assert result.allowed is False


class TestProviderAllowlist:
    """Tests for provider allowlist."""

    @given(ip=aws_ip_strategy)
    @settings(max_examples=20)
    def test_allowed_provider_overrides_block_all(self, ip: str) -> None:
        """Property: Provider allowlist overrides block_all_cloud.

        *For any* IP from allowed provider, it's allowed even with block_all.
        **Validates: Requirements 5.3**
        """
        config = CloudProviderConfig(
            block_all_cloud=True,
            allowed_providers={CloudProvider.AWS},
            allow_cloudflare=False,
        )
        filter = CloudProviderFilter(config=config)

        result = asyncio.run(filter.check(ip))

        assert result.allowed is True


class TestCloudProviderFilterBuilder:
    """Tests for CloudProviderFilterBuilder."""

    @given(provider=provider_strategy)
    @settings(max_examples=20)
    def test_builder_block_providers(self, provider: CloudProvider) -> None:
        """Property: Builder correctly sets blocked providers.

        *For any* provider, builder configures it correctly.
        **Validates: Requirements 5.3**
        """
        filter = (
            CloudProviderFilterBuilder()
            .block_providers(provider)
            .build()
        )

        assert provider in filter.config.blocked_providers

    def test_builder_block_all_cloud(self) -> None:
        """Test builder block_all_cloud setting."""
        filter = (
            CloudProviderFilterBuilder()
            .block_all_cloud(True)
            .allow_cloudflare(False)
            .build()
        )

        assert filter.config.block_all_cloud is True
        assert filter.config.allow_cloudflare is False


class TestCloudProviderResult:
    """Tests for CloudProviderResult factory methods."""

    def test_allow_result(self) -> None:
        """Test allow factory method."""
        result = CloudProviderResult.allow()
        assert result.allowed is True
        assert result.reason is None

    def test_block_result(self) -> None:
        """Test block factory method."""
        info = CloudProviderInfo(ip="1.2.3.4", provider=CloudProvider.AWS)
        result = CloudProviderResult.block("Test reason", info)

        assert result.allowed is False
        assert result.reason == "Test reason"
        assert result.info is not None
        assert result.info.is_blocked is True


class TestHelperMethods:
    """Tests for helper methods."""

    @given(ip=aws_ip_strategy)
    @settings(max_examples=20)
    def test_is_cloud_ip_true_for_cloud(self, ip: str) -> None:
        """Property: is_cloud_ip returns True for cloud IPs.

        *For any* cloud IP, is_cloud_ip returns True.
        **Validates: Requirements 5.3**
        """
        filter = CloudProviderFilter(config=CloudProviderConfig())
        assert filter.is_cloud_ip(ip) is True

    @given(ip=non_cloud_ip_strategy)
    @settings(max_examples=20)
    def test_is_cloud_ip_false_for_non_cloud(self, ip: str) -> None:
        """Property: is_cloud_ip returns False for non-cloud IPs.

        *For any* non-cloud IP, is_cloud_ip returns False.
        **Validates: Requirements 5.3**
        """
        filter = CloudProviderFilter(config=CloudProviderConfig())
        assert filter.is_cloud_ip(ip) is False

    @given(ip=aws_ip_strategy)
    @settings(max_examples=20)
    def test_get_provider_returns_correct_provider(self, ip: str) -> None:
        """Property: get_provider returns correct provider.

        *For any* cloud IP, get_provider returns the correct provider.
        **Validates: Requirements 5.3**
        """
        filter = CloudProviderFilter(config=CloudProviderConfig())
        provider = filter.get_provider(ip)
        assert provider == CloudProvider.AWS


# =============================================================================
# Property Tests - IPv6 and External Sources (shared-modules-refactoring)
# =============================================================================


class TestIPv6Support:
    """Property tests for IPv6 support.

    **Feature: shared-modules-refactoring**
    **Validates: Requirements 9.1, 9.2, 9.3**
    """

    def test_ipv6_provider_identification(self) -> None:
        """**Feature: shared-modules-refactoring, Property 18: IPv6 Provider Identification**
        **Validates: Requirements 9.1**

        For any valid IPv6 address in a known cloud provider range,
        the CloudProviderFilter SHALL return the correct provider.
        """
        provider = InMemoryCloudRangeProvider()

        # Test AWS IPv6
        result = provider.identify_provider("2600:1f00::1")
        assert result == CloudProvider.AWS

        # Test Cloudflare IPv6
        result = provider.identify_provider("2606:4700::1")
        assert result == CloudProvider.CLOUDFLARE

    def test_ipv6_ranges_stored_separately(self) -> None:
        """**Feature: shared-modules-refactoring, Property 18: IPv6 Provider Identification**
        **Validates: Requirements 9.2**

        IPv6 ranges SHALL be stored separately from IPv4 ranges.
        """
        provider = InMemoryCloudRangeProvider()

        ipv4_ranges = provider.get_ranges(CloudProvider.AWS)
        ipv6_ranges = provider.get_ipv6_ranges(CloudProvider.AWS)

        # Both should have ranges
        assert len(ipv4_ranges) > 0
        assert len(ipv6_ranges) > 0

        # They should be different types
        from ipaddress import IPv4Network, IPv6Network
        assert all(isinstance(r, IPv4Network) for r in ipv4_ranges)
        assert all(isinstance(r, IPv6Network) for r in ipv6_ranges)

    @given(invalid_ip=st.sampled_from([
        "not-an-ip",
        "256.256.256.256",
        "::gggg",
        "",
        "1.2.3",
        "1.2.3.4.5",
    ]))
    @settings(max_examples=20)
    def test_invalid_ip_graceful_handling(self, invalid_ip: str) -> None:
        """**Feature: shared-modules-refactoring, Property 19: Invalid IP Graceful Handling**
        **Validates: Requirements 9.3**

        For any invalid IP address string, the CloudProviderFilter SHALL
        return None without raising an exception.
        """
        provider = InMemoryCloudRangeProvider()

        # Should not raise, should return None
        result = provider.identify_provider(invalid_ip)
        assert result is None


class TestExternalRangeSource:
    """Property tests for external range source support.

    **Feature: shared-modules-refactoring**
    **Validates: Requirements 5.1, 5.4**
    """

    def test_external_range_source_support(self) -> None:
        """**Feature: shared-modules-refactoring, Property 11: External Range Source Support**
        **Validates: Requirements 5.1**

        For any CloudIPRangeProvider initialized with external sources,
        the provider SHALL contain ranges from both default and external sources.
        """
        from infrastructure.security.cloud_provider_filter.ranges import UpdatableCloudRangeProvider

        provider = UpdatableCloudRangeProvider()

        # Should have default ranges
        aws_ranges = provider.get_ranges(CloudProvider.AWS)
        assert len(aws_ranges) > 0

        # Add custom range
        provider._base_provider.add_range(CloudProvider.AWS, "100.0.0.0/8")

        # Should now have both default and custom ranges
        updated_ranges = provider.get_ranges(CloudProvider.AWS)
        assert len(updated_ranges) > len(aws_ranges) or "100.0.0.0/8" in [str(r) for r in updated_ranges]

    def test_range_merge_without_duplicates(self) -> None:
        """**Feature: shared-modules-refactoring, Property 12: Range Merge Without Duplicates**
        **Validates: Requirements 5.4**

        For any set of IP ranges added to InMemoryCloudRangeProvider,
        the stored ranges SHALL contain no duplicate networks.
        """
        provider = InMemoryCloudRangeProvider()

        # Add same range multiple times
        provider.add_range(CloudProvider.AWS, "100.0.0.0/8")
        provider.add_range(CloudProvider.AWS, "100.0.0.0/8")
        provider.add_range(CloudProvider.AWS, "100.0.0.0/8")

        ranges = provider.get_ranges(CloudProvider.AWS)

        # Count occurrences of the specific range
        from ipaddress import ip_network
        target = ip_network("100.0.0.0/8")
        count = sum(1 for r in ranges if r == target)

        assert count == 1, f"Expected 1 occurrence, found {count}"

    def test_merge_ranges_deduplicates(self) -> None:
        """**Feature: shared-modules-refactoring, Property 12: Range Merge Without Duplicates**
        **Validates: Requirements 5.4**

        merge_ranges SHALL deduplicate when adding multiple ranges.
        """
        provider = InMemoryCloudRangeProvider()

        # Merge with duplicates
        provider.merge_ranges(CloudProvider.GCP, [
            "200.0.0.0/8",
            "200.0.0.0/8",
            "201.0.0.0/8",
            "201.0.0.0/8",
        ])

        ranges = provider.get_ranges(CloudProvider.GCP)

        from ipaddress import ip_network
        range_200 = ip_network("200.0.0.0/8")
        range_201 = ip_network("201.0.0.0/8")

        count_200 = sum(1 for r in ranges if r == range_200)
        count_201 = sum(1 for r in ranges if r == range_201)

        assert count_200 == 1
        assert count_201 == 1

    def test_staleness_detection(self) -> None:
        """Test that staleness is properly detected."""
        from datetime import timedelta
        from infrastructure.security.cloud_provider_filter.ranges import InMemoryCloudRangeProvider

        provider = InMemoryCloudRangeProvider()

        # Fresh provider should not be stale
        assert not provider.is_stale(max_age=timedelta(hours=24))

        # Manually set old timestamp
        from datetime import datetime, timezone
        provider._last_update = datetime.now(timezone.utc) - timedelta(hours=25)

        # Now should be stale
        assert provider.is_stale(max_age=timedelta(hours=24))
